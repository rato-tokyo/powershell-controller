"""
PowerShellコマンド実行モジュール

PowerShellコマンドの実行に関する機能を提供します。
"""

import asyncio
import threading
import time
from typing import Optional, Union

from loguru import logger

from .errors import PowerShellError, PowerShellExecutionError
from .interfaces import CommandResultProtocol, SessionProtocol
from .session import PowerShellSession
from .utils.command_result import CommandResult


class CommandExecutor:
    """
    PowerShellコマンド実行クラス

    コマンドの実行に関する機能を提供します。
    """

    def __init__(self, session: Union[PowerShellSession, SessionProtocol]):
        """
        コマンド実行クラスを初期化します。

        Args:
            session: PowerShellセッション
        """
        self._session: Union[PowerShellSession, SessionProtocol] = session
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock: threading.RLock = threading.RLock()
        logger.debug("CommandExecutorが初期化されました")

    async def run_command(
        self, command: str, timeout: Optional[float] = None
    ) -> CommandResultProtocol:
        """
        PowerShellコマンドを実行します。

        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）

        Returns:
            CommandResultProtocol: コマンドの実行結果

        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
        """
        start_time: float = time.time()
        try:
            output: str = await self._session.execute(command, timeout)
            execution_time: float = time.time() - start_time

            result: CommandResultProtocol = CommandResult(
                output=output,
                error="",
                success=True,
                command=command,
                execution_time=execution_time,
            )
            return result

        except PowerShellError as e:
            execution_time: float = time.time() - start_time
            error_message: str = str(e)
            logger.error(f"コマンドの実行に失敗しました: {error_message}")

            result: CommandResultProtocol = CommandResult(
                output="",
                error=error_message,
                success=False,
                command=command,
                execution_time=execution_time,
            )
            return result

        except Exception as e:
            execution_time: float = time.time() - start_time
            error_message: str = str(e)
            logger.error(f"予期しないエラーが発生しました: {error_message}")

            result: CommandResultProtocol = CommandResult(
                output="",
                error=f"予期しないエラー: {error_message}",
                success=False,
                command=command,
                execution_time=execution_time,
            )
            return result

    async def run_script(
        self, script: str, timeout: Optional[float] = None
    ) -> CommandResultProtocol:
        """
        PowerShellスクリプトを実行します。

        Args:
            script: 実行するスクリプト
            timeout: タイムアウト時間（秒）

        Returns:
            CommandResultProtocol: スクリプトの実行結果

        Raises:
            PowerShellExecutionError: スクリプトの実行に失敗した場合
        """
        # スクリプト実行はコマンド実行と同じ処理を行う
        script_result: CommandResultProtocol = await self.run_command(script, timeout)
        return script_result

    async def execute_command(self, command: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellコマンドを実行し、文字列結果を返します。

        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）

        Returns:
            str: コマンドの実行結果（文字列）

        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
        """
        try:
            effective_timeout: Optional[float] = timeout
            result: str = await self._session.execute(command, effective_timeout)
            return result
        except Exception as e:
            error_message: str = str(e)
            logger.error(f"PowerShellコマンドの実行に失敗: {error_message}")
            raise PowerShellExecutionError(
                f"コマンド実行中にエラーが発生しました: {error_message}"
            ) from e

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
                thread: threading.Thread = threading.Thread(
                    target=self._run_event_loop, args=(self._loop,), daemon=True
                )
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
