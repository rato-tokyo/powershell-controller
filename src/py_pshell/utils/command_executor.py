"""
コマンド実行モジュール

PowerShellコマンドの実行を管理するクラスを提供します。
"""

import time
from typing import Protocol

from loguru import logger

from py_pshell.interfaces import CommandResultProtocol
from py_pshell.utils.command_result import CommandResult


class SessionProtocol(Protocol):
    """セッションプロトコル"""

    async def execute(self, command: str, timeout: float | None = None) -> str:
        """コマンドを実行"""
        ...


class CommandExecutor:
    """コマンド実行クラス

    PowerShellコマンドの実行を管理するクラスです。
    """

    def __init__(self, session: SessionProtocol) -> None:
        """初期化

        Args:
            session: PowerShellセッション
        """
        self._session: SessionProtocol = session

    async def run_command(
        self, command: str, timeout: float | None = None
    ) -> CommandResultProtocol:
        """コマンドを実行します。

        Args:
            command: 実行するコマンド
            timeout: タイムアウト時間（秒）

        Returns:
            CommandResultProtocol: コマンドの実行結果

        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
        """
        start_time: float = time.time()
        try:
            output: str = await self._session.execute(command, timeout)
            execution_time: float = time.time() - start_time
            return CommandResult(
                output=output,
                error="",
                success=True,
                command=command,
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time: float = time.time() - start_time
            logger.error(f"コマンドの実行に失敗しました: {e}")
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                command=command,
                execution_time=execution_time,
            )

    async def run_script(self, script: str, timeout: float | None = None) -> CommandResultProtocol:
        """スクリプトを実行します。

        Args:
            script: 実行するスクリプト
            timeout: タイムアウト時間（秒）

        Returns:
            CommandResultProtocol: スクリプトの実行結果

        Raises:
            PowerShellExecutionError: スクリプトの実行に失敗した場合
        """
        return await self.run_command(script, timeout)
