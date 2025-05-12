"""
PowerShellコントローラーモジュール

PowerShellコマンドの実行を制御するクラスを提供します。
"""
import asyncio
from typing import Any, Dict, Optional, Union
from loguru import logger
from result import Result, Ok, Err

from py_pshell.interfaces import (
    PowerShellControllerProtocol,
    CommandResultProtocol,
    PowerShellControllerSettings
)
from py_pshell.errors import (
    PowerShellExecutionError,
    PowerShellStartupError,
    PowerShellShutdownError
)
from py_pshell.utils.command_result import CommandResult
from py_pshell.utils.command_executor import CommandExecutor


class PowerShellController(PowerShellControllerProtocol):
    """PowerShellコントローラー

    PowerShellコマンドの実行を制御するクラスです。
    非同期コンテキストマネージャーとして使用できます。
    """

    def __init__(self, settings: Optional[PowerShellControllerSettings] = None):
        """初期化

        Args:
            settings: コントローラーの設定
        """
        self._settings = settings or PowerShellControllerSettings()
        self._session = None
        self._command_executor = None
        self._loop = None

    async def __aenter__(self) -> "PowerShellController":
        """非同期コンテキストマネージャーのエントリーポイント

        Returns:
            PowerShellController: 自身のインスタンス
        """
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
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
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # イベントループが実行中の場合は、非同期タスクを作成して実行
                    future = asyncio.run_coroutine_threadsafe(self.close(), loop)
                    # 完了を待機（タイムアウトを設定）
                    future.result(timeout=self._settings.timeout_settings.shutdown)
                else:
                    # イベントループが実行中でない場合は、同期的に実行
                    loop.run_until_complete(self.close())
            except Exception as e:
                logger.error(f"PowerShellセッションの終了に失敗しました: {e}")
                raise PowerShellShutdownError(f"セッションの終了に失敗しました: {e}") from e
            finally:
                self._session = None
                self._command_executor = None

    async def execute_command(self, command: str, timeout: Optional[float] = None) -> str:
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
            result = await self._session.execute(command, timeout)
            logger.debug(f"コマンドを実行しました: {command}")
            return result
        except Exception as e:
            logger.error(f"コマンドの実行に失敗しました: {e}")
            raise PowerShellExecutionError(f"コマンドの実行に失敗しました: {e}") from e

    async def run_command(self, command: str, timeout: Optional[float] = None) -> CommandResultProtocol:
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
            result = await self._command_executor.run_command(command, timeout)
            logger.debug(f"コマンドを実行しました: {command}")
            return result
        except Exception as e:
            logger.error(f"コマンドの実行に失敗しました: {e}")
            raise PowerShellExecutionError(f"コマンドの実行に失敗しました: {e}") from e

    async def run_script(self, script: str, timeout: Optional[float] = None) -> CommandResultProtocol:
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
            result = await self._command_executor.run_script(script, timeout)
            logger.debug("スクリプトを実行しました")
            return result
        except Exception as e:
            logger.error(f"スクリプトの実行に失敗しました: {e}")
            raise PowerShellExecutionError(f"スクリプトの実行に失敗しました: {e}") from e

    async def get_json(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
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
            result = await self._session.execute(command, timeout)
            logger.debug(f"JSONを取得しました: {command}")
            return self._parse_json(result)
        except Exception as e:
            logger.error(f"JSONの取得に失敗しました: {e}")
            raise PowerShellExecutionError(f"JSONの取得に失敗しました: {e}") from e

    async def _create_session(self) -> Any:
        """PowerShellセッションを作成します。

        Returns:
            Any: 作成されたセッション

        Raises:
            PowerShellStartupError: セッションの作成に失敗した場合
        """
        try:
            # セッションの作成処理を実装
            return None
        except Exception as e:
            logger.error(f"セッションの作成に失敗しました: {e}")
            raise PowerShellStartupError(f"セッションの作成に失敗しました: {e}") from e

    def _parse_json(self, json_str: str) -> Dict[str, Any]:
        """JSON文字列をパースします。

        Args:
            json_str: パースするJSON文字列

        Returns:
            Dict[str, Any]: パースされたJSON

        Raises:
            PowerShellExecutionError: JSONのパースに失敗した場合
        """
        try:
            import json
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSONのパースに失敗しました: {e}")
            raise PowerShellExecutionError(f"JSONのパースに失敗しました: {e}") from e
