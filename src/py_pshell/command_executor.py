"""
PowerShellコマンド実行モジュール

PowerShellコマンドの実行に関する機能を提供します。
"""
import asyncio
import threading
from typing import Optional

from loguru import logger

from .config import PowerShellControllerSettings
from .errors import PowerShellError, PowerShellExecutionError
from .session import PowerShellSession
from .utils.command_result import CommandResult


class CommandExecutor:
    """
    PowerShellコマンド実行クラス

    コマンドの実行に関する機能を提供します。
    """

    def __init__(self, settings: PowerShellControllerSettings):
        """
        コマンド実行クラスを初期化します。

        Args:
            settings: コントローラーの設定
        """
        self.settings = settings
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.RLock()
        logger.debug("CommandExecutorが初期化されました")

    async def run_command(self, session: PowerShellSession, command: str, timeout: Optional[float] = None) -> CommandResult:
        """
        PowerShellコマンドを実行します。

        Args:
            session: PowerShellセッション
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）

        Returns:
            CommandResult: コマンドの実行結果
        """
        import time
        start_time = time.time()
        try:
            output = await session.execute(command, timeout)
            elapsed = time.time() - start_time

            return CommandResult(
                output=output,
                error="",
                success=True,
                command=command,
                execution_time=elapsed
            )
        except PowerShellError as e:
            elapsed = time.time() - start_time
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                command=command,
                execution_time=elapsed
            )

    async def execute_command(self, session: PowerShellSession, command: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellコマンドを実行します。

        Args:
            session: PowerShellセッション
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）

        Returns:
            str: コマンドの実行結果

        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
        """
        try:
            timeout_value = timeout or self.settings.timeout.command
            return await session.execute(command, timeout_value)
        except Exception as e:
            logger.error(f"PowerShellコマンドの実行に失敗: {e}")
            raise PowerShellExecutionError(f"コマンド実行中にエラーが発生しました: {e}") from e

    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """
        イベントループを取得または作成します。

        Returns:
            asyncio.AbstractEventLoop: イベントループ
        """
        with self._lock:
            if self._loop is None or self._loop.is_closed():
                # 新しいループを作成
                if hasattr(asyncio, "get_running_loop"):
                    try:
                        self._loop = asyncio.get_running_loop()
                    except RuntimeError:
                        # 実行中のループがない場合は新しいループを作成
                        self._loop = asyncio.new_event_loop()
                else:
                    self._loop = asyncio.new_event_loop()

                # ループを別スレッドで実行
                thread = threading.Thread(target=self._run_event_loop, args=(self._loop,), daemon=True)
                thread.start()

            return self._loop

    def _run_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        イベントループを実行します。

        Args:
            loop: 実行するイベントループ
        """
        asyncio.set_event_loop(loop)
        loop.run_forever()
