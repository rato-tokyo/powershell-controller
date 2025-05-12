"""
PowerShellコントローラーのテスト用ユーティリティ

テストの実行に必要なモックやヘルパー関数を提供します。
"""

import os
import platform
import tempfile
from typing import Any, Dict, List, Optional, Union

import pytest
from loguru import logger

from py_pshell.controller import CommandResult
from py_pshell.errors import PowerShellExecutionError
from py_pshell.interfaces import CommandResultProtocol, PowerShellControllerProtocol

# テスト環境の情報
IS_WINDOWS = platform.system().lower() == "windows"
IS_CI = "CI" in os.environ


class MockCommandResult(CommandResult):
    """
    モックコマンド結果
    """

    def __init__(self, output: str = "", error: str = "", success: bool = True, command: str = ""):
        super().__init__(
            output=output, error=error, success=success, command=command, execution_time=0.0
        )


class MockPowerShellController(PowerShellControllerProtocol):
    """
    モックPowerShellコントローラー

    テストで使用するためのモックコントローラーです。
    """

    def __init__(
        self,
        command_responses: Dict[str, Union[str, Exception]] = None,
        default_response: str = "",
        raise_on_unknown: bool = False,
    ):
        """
        モックコントローラーを初期化します。

        Args:
            command_responses: コマンドとその応答のマッピング
            default_response: デフォルトの応答
            raise_on_unknown: 未知のコマンドでエラーを発生させるかどうか
        """
        self.command_responses = command_responses or {}
        self.default_response = default_response
        self.raise_on_unknown = raise_on_unknown
        self.executed_commands: List[str] = []
        self.closed = False

    async def run_command(
        self, command: str, timeout: Optional[float] = None
    ) -> CommandResultProtocol:
        """
        コマンドを実行します（モック）
        """
        self.executed_commands.append(command)
        return self._get_result(command)

    async def run_script(
        self, script: str, timeout: Optional[float] = None
    ) -> CommandResultProtocol:
        """
        スクリプトを実行します（モック）
        """
        self.executed_commands.append(script)
        return self._get_result(script)

    def execute_command(self, command: str, timeout: Optional[float] = None) -> str:
        """
        コマンドを同期的に実行します（モック）
        """
        self.executed_commands.append(command)
        result = self._get_result(command)
        if not result.success:
            raise PowerShellExecutionError(result.error, command)
        return result.output

    def execute_script(self, script: str, timeout: Optional[float] = None) -> str:
        """
        スクリプトを同期的に実行します（モック）
        """
        return self.execute_command(script, timeout)

    def get_json(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        コマンドを実行しJSON形式で結果を返します（モック）
        """
        import json

        output = self.execute_command(command, timeout)
        return json.loads(output)

    async def close(self) -> None:
        """
        コントローラーを閉じます（モック）
        """
        self.closed = True

    def close_sync(self) -> None:
        """
        コントローラーを同期的に閉じます（モック）
        """
        self.closed = True

    def _get_result(self, command: str) -> CommandResult:
        """
        指定されたコマンドの実行結果を返します。

        Args:
            command: 実行するコマンド

        Returns:
            CommandResult: コマンド実行結果
        """
        if command in self.command_responses:
            response = self.command_responses[command]
            if isinstance(response, Exception):
                return CommandResult(
                    output="",
                    error=str(response),
                    success=False,
                    command=command,
                    execution_time=0.0,
                )
            return CommandResult(
                output=response, error="", success=True, command=command, execution_time=0.0
            )
        elif self.raise_on_unknown:
            return CommandResult(
                output="",
                error="Unknown command",
                success=False,
                command=command,
                execution_time=0.0,
            )
        else:
            return CommandResult(
                output=self.default_response,
                error="",
                success=True,
                command=command,
                execution_time=0.0,
            )


def create_powershell_script(content: str) -> str:
    """
    テスト用のPowerShellスクリプトファイルを作成します。

    Args:
        content: スクリプトの内容

    Returns:
        str: 作成されたスクリプトファイルのパス
    """
    fd, path = tempfile.mkstemp(suffix=".ps1", prefix="test_script_", text=True)
    try:
        os.write(fd, content.encode("utf-8"))
    finally:
        os.close(fd)
    return path


def cleanup_temp_file(path: str) -> None:
    """
    一時ファイルを削除します。

    Args:
        path: 削除するファイルのパス
    """
    try:
        if os.path.exists(path):
            os.unlink(path)
    except Exception as e:
        logger.warning(f"一時ファイルの削除に失敗しました: {e}")


@pytest.fixture
def mock_controller():
    """
    モックPowerShellコントローラーを提供するフィクスチャ
    """
    return MockPowerShellController(
        command_responses={
            "Get-Process": "Process1\nProcess2\nProcess3",
            "Get-Date": "2023-01-01",
            "Get-Error": PowerShellExecutionError("エラーが発生しました", "Get-Error"),
            "Get-Process | ConvertTo-Json": '[{"Name": "Process1", "Id": 123}, {"Name": "Process2", "Id": 456}]',
        },
        default_response="Default Response",
    )


@pytest.fixture
def temp_script():
    """
    テスト用の一時スクリプトファイルを提供するフィクスチャ
    """
    script_content = """
    param (
        [string]$Name = "Default",
        [int]$Value = 0
    )
    
    $output = @{
        Name = $Name
        Value = $Value
        Date = Get-Date -Format "yyyy-MM-dd"
    }
    
    $output | ConvertTo-Json
    """

    script_path = create_powershell_script(script_content)
    yield script_path
    cleanup_temp_file(script_path)
