"""
PowerShellストリーム処理モジュール

PowerShellプロセスとの入出力ストリームを管理する機能を提供します。
"""
import asyncio
from typing import Optional, Tuple

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import PowerShellControllerSettings
from .errors import PowerShellStreamError, PowerShellExecutionError


class StreamHandler:
    """
    PowerShellストリーム処理クラス

    PowerShellプロセスとの入出力ストリームを管理します。
    """

    def __init__(self, settings: PowerShellControllerSettings):
        """
        ストリーム処理クラスを初期化します。

        Args:
            settings: セッションの設定
        """
        self.settings = settings
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
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
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
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

            init_script = (
                "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
                "[Console]::InputEncoding = [System.Text.Encoding]::UTF8\n"
            )

            self._writer.write(init_script.encode(self.settings.encoding))
            await asyncio.wait_for(self._writer.drain(), timeout=5.0)
            logger.debug("初期化スクリプトを送信しました")

        except asyncio.TimeoutError as e:
            logger.error("初期化スクリプトの送信がタイムアウトしました")
            raise PowerShellStreamError("初期化スクリプトの送信がタイムアウトしました") from e
        except Exception as e:
            logger.error(f"初期化スクリプトの送信に失敗: {e}")
            raise PowerShellStreamError(f"初期化スクリプトの送信に失敗しました: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
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

            self._writer.write(f"{command}\n".encode(self.settings.encoding))
            await asyncio.wait_for(self._writer.drain(), timeout=5.0)

        except asyncio.TimeoutError as e:
            logger.error("コマンドの送信がタイムアウトしました")
            raise PowerShellStreamError("コマンドの送信がタイムアウトしました") from e
        except Exception as e:
            logger.error(f"コマンドの送信に失敗: {e}")
            raise PowerShellStreamError(f"コマンドの送信に失敗しました: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def read_output(self, timeout: Optional[float] = None) -> str:
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

            output = bytearray()
            try:
                while True:
                    chunk = await asyncio.wait_for(
                        self._reader.read(4096),
                        timeout=timeout or self.settings.timeout.command
                    )
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > 1024 * 1024:  # 1MB以上のデータは読み取らない
                        break
            except asyncio.TimeoutError:
                pass  # タイムアウトは正常な終了条件として扱う

            return output.decode(self.settings.encoding)

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

    async def execute_command(self, command: str, timeout: Optional[float] = None) -> str:
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
            output = await self.read_output(timeout)
            
            # 出力から成功/失敗を判定
            if "COMMAND_ERROR" in output:
                error_msg = output.split("COMMAND_ERROR")[0].strip()
                raise PowerShellExecutionError(f"コマンドの実行に失敗しました: {error_msg}", command)
            
            # 成功メッセージを除去
            result = output.split("COMMAND_SUCCESS")[0].strip()
            return result

        except PowerShellStreamError as e:
            raise PowerShellExecutionError(f"コマンドの実行に失敗しました: {e}", command) from e
        except Exception as e:
            raise PowerShellExecutionError(f"コマンドの実行に失敗しました: {e}", command) from e
