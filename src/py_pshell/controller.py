"""
PowerShellコントローラーモジュール

PowerShellコマンドの実行を制御するクラスを提供します。
"""

import asyncio
import json
import types
from typing import Any, TypeVar

from loguru import logger

from py_pshell.errors import (
    PowerShellExecutionError,
    PowerShellShutdownError,
    PowerShellStartupError,
)
from py_pshell.interfaces import (
    CommandResultProtocol,
    PowerShellControllerProtocol,
    PowerShellControllerSettings,
    SessionProtocol,
)
from py_pshell.utils.command_executor import CommandExecutor

T = TypeVar("T")


class PowerShellController(PowerShellControllerProtocol):
    """PowerShellコントローラー

    PowerShellコマンドの実行を制御するクラスです。
    非同期コンテキストマネージャーとして使用できます。
    """

    def __init__(self, settings: PowerShellControllerSettings | None = None) -> None:
        """初期化

        Args:
            settings: コントローラーの設定
        """
        self._settings: PowerShellControllerSettings = settings or PowerShellControllerSettings()
        self._session: SessionProtocol | None = None
        self._command_executor: CommandExecutor | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def __aenter__(self) -> "PowerShellController":
        """非同期コンテキストマネージャーのエントリーポイント

        Returns:
            PowerShellController: 自身のインスタンス
        """
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: type | None, exc_val: Exception | None, exc_tb: types.TracebackType | None
    ) -> None:
        """非同期コンテキストマネージャーのエグジットポイント

        Args:
            exc_type: 例外の型
            exc_val: 例外の値
            exc_tb: トレースバック
        """
        await self.close()

    async def start(self) -> None:
        """セッションを開始します。

        Raises:
            PowerShellStartupError: セッションの開始に失敗した場合
        """
        try:
            if not self._session:
                self._session = await self._create_session()
                if not self._session:
                    raise PowerShellStartupError("セッションの作成に失敗しました")
                self._command_executor = CommandExecutor(self._session)
                logger.info("PowerShellセッションを開始しました")
        except Exception as e:
            logger.error(f"PowerShellセッションの開始に失敗しました: {e}")
            raise PowerShellStartupError(f"セッションの開始に失敗しました: {e}") from e

    async def close(self) -> None:
        """セッションを終了します。

        Raises:
            PowerShellShutdownError: セッションの終了に失敗した場合
        """
        if self._session:
            try:
                await self._session.stop()
            except Exception as e:
                logger.error(f"PowerShellセッションの終了に失敗しました: {e}")
                raise PowerShellShutdownError(f"セッションの終了に失敗しました: {e}") from e
            finally:
                self._session = None
                self._command_executor = None
                logger.info("PowerShellセッションを終了しました")

    def close_sync(self) -> None:
        """セッションを同期的に終了します。

        Raises:
            PowerShellShutdownError: セッションの終了に失敗した場合
        """
        if self._session:
            try:
                # 既存のイベントループを取得
                loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
                if loop.is_running():
                    # イベントループが実行中の場合は、非同期タスクを作成して実行
                    future: asyncio.Future[None] = asyncio.run_coroutine_threadsafe(
                        self.close(), loop
                    )
                    # 完了を待機（タイムアウトを設定）
                    timeout_value: float = self._settings.timeout
                    future.result(timeout=timeout_value)
                else:
                    # イベントループが実行中でない場合は、同期的に実行
                    loop.run_until_complete(self.close())
            except Exception as e:
                logger.error(f"PowerShellセッションの終了に失敗しました: {e}")
                raise PowerShellShutdownError(f"セッションの終了に失敗しました: {e}") from e
            finally:
                self._session = None
                self._command_executor = None

    async def execute_command(self, command: str, timeout: float | None = None) -> str:
        """PowerShellコマンドを実行します。

        Args:
            command: 実行するコマンド
            timeout: タイムアウト時間（秒）

        Returns:
            str: コマンドの出力

        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
        """
        if not self._session:
            raise PowerShellExecutionError("セッションが開始されていません")

        try:
            result: str = await self._session.execute(command, timeout)
            logger.debug(f"コマンドを実行しました: {command}")
            return result
        except Exception as e:
            logger.error(f"コマンドの実行に失敗しました: {e}")
            raise PowerShellExecutionError(f"コマンドの実行に失敗しました: {e}") from e

    async def run_command(
        self, command: str, timeout: float | None = None
    ) -> CommandResultProtocol:
        """PowerShellコマンドを実行し、結果を返します。

        Args:
            command: 実行するコマンド
            timeout: タイムアウト時間（秒）

        Returns:
            CommandResultProtocol: コマンドの実行結果

        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
        """
        if not self._command_executor:
            raise PowerShellExecutionError("セッションが開始されていません")

        try:
            result: CommandResultProtocol = await self._command_executor.run_command(
                command, timeout
            )
            logger.debug(f"コマンドを実行しました: {command}")
            return result
        except Exception as e:
            logger.error(f"コマンドの実行に失敗しました: {e}")
            raise PowerShellExecutionError(f"コマンドの実行に失敗しました: {e}") from e

    async def run_script(self, script: str, timeout: float | None = None) -> CommandResultProtocol:
        """PowerShellスクリプトを実行し、結果を返します。

        Args:
            script: 実行するスクリプト
            timeout: タイムアウト時間（秒）

        Returns:
            CommandResultProtocol: スクリプトの実行結果

        Raises:
            PowerShellExecutionError: スクリプトの実行に失敗した場合
        """
        if not self._command_executor:
            raise PowerShellExecutionError("セッションが開始されていません")

        try:
            result: CommandResultProtocol = await self._command_executor.run_script(script, timeout)
            logger.debug("スクリプトを実行しました")
            return result
        except Exception as e:
            logger.error(f"スクリプトの実行に失敗しました: {e}")
            raise PowerShellExecutionError(f"スクリプトの実行に失敗しました: {e}") from e

    async def get_json(self, command: str, timeout: float | None = None) -> dict[str, Any]:
        """PowerShellコマンドを実行し、結果をJSONとして返します。

        Args:
            command: 実行するコマンド
            timeout: タイムアウト時間（秒）

        Returns:
            Dict[str, Any]: JSONとしてパースされた結果

        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
        """
        if not self._session:
            raise PowerShellExecutionError("セッションが開始されていません")

        try:
            result: str = await self._session.execute(command, timeout)
            logger.debug(f"JSONを取得しました: {command}")
            return self._parse_json(result)
        except Exception as e:
            logger.error(f"JSONの取得に失敗しました: {e}")
            raise PowerShellExecutionError(f"JSONの取得に失敗しました: {e}") from e

    async def _create_session(self) -> SessionProtocol | None:
        """PowerShellセッションを作成します。

        Returns:
            SessionProtocol | None: 作成されたセッション

        Raises:
            PowerShellStartupError: セッションの作成に失敗した場合
        """
        try:
            # セッションの作成処理を実装
            return None
        except Exception as e:
            logger.error(f"セッションの作成に失敗しました: {e}")
            raise PowerShellStartupError(f"セッションの作成に失敗しました: {e}") from e

    def _parse_json(self, json_str: str) -> dict[str, Any]:
        """JSON文字列をパースします。

        Args:
            json_str: パースするJSON文字列

        Returns:
            Dict[str, Any]: パースされたJSON

        Raises:
            PowerShellExecutionError: JSONのパースに失敗した場合
        """
        try:
            # 文字列の前後の空白を削除
            json_str = json_str.strip()
            # JSONをパース
            result: dict[str, Any] = json.loads(json_str)
            return result
        except Exception as e:
            logger.error(f"JSONのパースに失敗しました: {e}")
            raise PowerShellExecutionError(f"JSONのパースに失敗しました: {e}") from e
