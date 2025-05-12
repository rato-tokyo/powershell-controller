"""
PowerShellセッション管理モジュール

PowerShellとの接続セッションを管理するためのクラスを提供します。
"""

import types
from typing import Optional, Type

from loguru import logger

from .config import PowerShellControllerSettings
from .errors import PowerShellShutdownError, PowerShellStartupError
from .process_manager import ProcessManager
from .stream_handler import StreamHandler


class PowerShellSession:
    """
    PowerShellセッションクラス
    PowerShellとの通信セッションを管理します。
    """

    def __init__(self, settings: PowerShellControllerSettings) -> None:
        """
        PowerShellセッションを初期化します。

        Args:
            settings: セッションの設定
        """
        self.settings = settings
        self._process_manager = ProcessManager(settings)
        self._stream_handler = StreamHandler(settings)
        self._is_running = False
        logger.debug("PowerShellSessionが初期化されました")

    async def __aenter__(self) -> "PowerShellSession":
        """
        非同期コンテキストマネージャーのエントリーポイント

        Returns:
            PowerShellSession: このセッションインスタンス
        """
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[types.TracebackType],
    ) -> None:
        """
        非同期コンテキストマネージャーの終了処理

        Args:
            exc_type: 発生した例外の型
            exc_val: 発生した例外のインスタンス
            exc_tb: 例外のトレースバック
        """
        await self.stop()

    async def start(self) -> None:
        """
        PowerShellセッションを開始します。

        Raises:
            PowerShellStartupError: PowerShellプロセスの起動に失敗した場合
        """
        if self._is_running:
            return

        try:
            reader, writer = await self._process_manager.start()
            self._stream_handler.set_streams(reader, writer)
            await self._stream_handler.initialize()
            self._is_running = True
            logger.info("PowerShellセッションが開始されました")
        except Exception as e:
            logger.error(f"PowerShellセッションの開始に失敗: {e}")
            raise PowerShellStartupError(f"PowerShellセッションの開始に失敗しました: {e}") from e

    async def stop(self) -> None:
        """
        PowerShellセッションを停止します。

        Raises:
            PowerShellShutdownError: PowerShellプロセスの終了に失敗した場合
        """
        if not self._is_running:
            return

        try:
            await self._process_manager.stop()
            self._is_running = False
            logger.info("PowerShellセッションが停止しました")
        except Exception as e:
            logger.error(f"PowerShellセッションの停止に失敗: {e}")
            raise PowerShellShutdownError(f"PowerShellセッションの停止に失敗しました: {e}") from e

    async def execute(self, command: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellコマンドを実行します。

        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）

        Returns:
            str: コマンドの実行結果

        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
            PowerShellTimeoutError: コマンドの実行がタイムアウトした場合
            CommunicationError: PowerShellとの通信に失敗した場合
        """
        return await self._stream_handler.execute_command(command, timeout)
