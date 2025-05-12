"""
PowerShellストリーム処理モジュール

PowerShellプロセスとの入出力ストリームを管理する機能を提供します。
"""

import asyncio
from typing import Final

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import PowerShellControllerSettings
from .errors import PowerShellExecutionError, PowerShellStreamError


class StreamHandler:
    """
    PowerShellストリーム処理クラス

    PowerShellプロセスとの入出力ストリームを管理します。
    """

    def __init__(self, settings: PowerShellControllerSettings) -> None:
        """
        ストリーム処理クラスを初期化します。

        Args:
            settings: セッションの設定
        """
        self.settings: PowerShellControllerSettings = settings
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        logger.debug("StreamHandlerが初期化されました")

    def set_streams(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        ストリームを設定します。

        Args:
            reader: 標準出力のストリーム
            writer: 標準入力のストリーム
        """
        self._reader = reader
        self._writer = writer

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True
    )
    async def send_init_script(self) -> None:
        """
        初期化スクリプトを送信します。

        Raises:
            PowerShellStreamError: スクリプトの送信に失敗した場合
        """
        try:
            if not self._writer:
                raise PowerShellStreamError("ストリームが初期化されていません")

            init_script: Final[str] = (
                "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Console]::InputEncoding = [System.Text.Encoding]::UTF8\n"
            )

            encoded_script: bytes = init_script.encode(self.settings.encoding)
            self._writer.write(encoded_script)
            await asyncio.wait_for(self._writer.drain(), timeout=5.0)
            logger.debug("初期化スクリプトを送信しました")

        except TimeoutError as e:
            logger.error("初期化スクリプトの送信がタイムアウトしました")
            raise PowerShellStreamError("初期化スクリプトの送信がタイムアウトしました") from e
        except Exception as e:
            logger.error(f"初期化スクリプトの送信に失敗: {e}")
            raise PowerShellStreamError(f"初期化スクリプトの送信に失敗しました: {e}") from e

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True
    )
    async def send_command(self, command: str) -> None:
        """
        コマンドを送信します。

        Args:
            command: 送信するコマンド

        Raises:
            PowerShellStreamError: コマンドの送信に失敗した場合
        """
        try:
            if not self._writer:
                raise PowerShellStreamError("ストリームが初期化されていません")

            encoded_command: bytes = f"{command}\n".encode(self.settings.encoding)
            self._writer.write(encoded_command)
            await asyncio.wait_for(self._writer.drain(), timeout=5.0)

        except TimeoutError as e:
            logger.error("コマンドの送信がタイムアウトしました")
            raise PowerShellStreamError("コマンドの送信がタイムアウトしました") from e
        except Exception as e:
            logger.error(f"コマンドの送信に失敗: {e}")
            raise PowerShellStreamError(f"コマンドの送信に失敗しました: {e}") from e

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True
    )
    async def read_output(self, timeout: float | None = None) -> str:
        """
        出力を読み取ります。

        Args:
            timeout: タイムアウト時間（秒）

        Returns:
            str: 読み取った出力

        Raises:
            PowerShellStreamError: 出力の読み取りに失敗した場合
        """
        try:
            if not self._reader:
                raise PowerShellStreamError("ストリームが初期化されていません")

            output: bytearray = bytearray()
            effective_timeout: float = timeout or self.settings.timeout
            max_size: int = 1024 * 1024  # 1MB
            chunk_size: int = 4096  # 4KB

            try:
                while True:
                    chunk: bytes = await asyncio.wait_for(
                        self._reader.read(chunk_size), timeout=effective_timeout
                    )
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > max_size:
                        break
            except TimeoutError:
                pass  # タイムアウトは正常な終了条件として扱う

            decoded_output: str = output.decode(self.settings.encoding)
            return decoded_output

        except Exception as e:
            logger.error(f"出力の読み取りに失敗: {e}")
            raise PowerShellStreamError(f"出力の読み取りに失敗しました: {e}") from e

    async def initialize(self) -> None:
        """
        ストリームを初期化します。

        Raises:
            PowerShellStreamError: 初期化に失敗した場合
        """
        await self.send_init_script()

    async def close(self) -> None:
        """
        ストリームを閉じます。
        """
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                logger.error(f"ストリームのクローズに失敗: {e}")
                error_msg: str = str(e)
                logger.debug(f"エラー詳細: {error_msg}")

    async def execute_command(self, command: str, timeout: float | None = None) -> str:
        """
        コマンドを実行し、結果を返します。

        Args:
            command: 実行するコマンド
            timeout: タイムアウト時間（秒）

        Returns:
            str: コマンドの実行結果

        Raises:
            PowerShellStreamError: ストリームの操作に失敗した場合
            PowerShellExecutionError: コマンドの実行に失敗した場合
        """
        try:
            await self.send_command(command)
            output: str = await self.read_output(timeout)

            error_marker: str = "COMMAND_ERROR"
            success_marker: str = "COMMAND_SUCCESS"

            # 出力から成功/失敗を判定
            if error_marker in output:
                split_result: list[str] = output.split(error_marker)
                error_msg: str = split_result[0].strip()
                raise PowerShellExecutionError(
                    f"コマンドの実行に失敗しました: {error_msg}", command
                )

            # 成功メッセージを除去
            split_result: list[str] = output.split(success_marker)
            result: str = split_result[0].strip()
            return result

        except PowerShellStreamError as e:
            error_msg: str = str(e)
            raise PowerShellExecutionError(
                f"コマンドの実行に失敗しました: {error_msg}", command
            ) from e
        except PowerShellExecutionError:
            raise
        except Exception as e:
            error_msg: str = str(e)
            raise PowerShellExecutionError(
                f"コマンドの実行に失敗しました: {error_msg}", command
            ) from e
