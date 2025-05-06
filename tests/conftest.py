"""
テスト用のコンフィギュレーション
"""
import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
import os
import json
import re
import platform
import sys
import time
import tempfile
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from powershell_controller.core.session import PowerShellSession
from powershell_controller.utils.config import PowerShellControllerSettings, RetryConfig, TimeoutConfig
from powershell_controller.simple import CommandResult
from loguru import logger

# テスト環境のプラットフォームを識別
TEST_PLATFORM = platform.system().lower()
IS_WINDOWS = TEST_PLATFORM == "windows"
IS_CI = os.environ.get("CI", "false").lower() == "true"
USE_MOCK = os.environ.get("POWERSHELL_TEST_MOCK", "true").lower() == "true"

# テスト実行の詳細情報をログに出力
logger.info(f"テスト環境: プラットフォーム={TEST_PLATFORM}, CI環境={IS_CI}, モック使用={USE_MOCK}")

@pytest.fixture(scope="session")
def event_loop_policy():
    """テスト用のイベントループポリシーを提供するフィクスチャ"""
    # Windows環境ではProactorEventLoopを使わないようにする
    if IS_WINDOWS:
        policy = asyncio.WindowsSelectorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        return policy
    return asyncio.get_event_loop_policy()

@pytest.fixture
def session_config() -> PowerShellControllerSettings:
    """テスト用のセッション設定を提供するフィクスチャ"""
    return PowerShellControllerSettings(
        log_level="DEBUG",
        timeouts=TimeoutConfig(
            default=60.0,    # タイムアウトを大幅に延長
            startup=60.0,    # 初期化タイムアウトを大幅に延長
            execution=15.0,  # 実行タイムアウトを延長
            read=3.0,        # 読み取りタイムアウトを延長
            shutdown=15.0,   # シャットダウンタイムアウトを延長
            cleanup=15.0     # クリーンアップタイムアウトを延長
        ),
        retry=RetryConfig(
            max_attempts=3,  # リトライ回数を増やす
            base_delay=0.5,
            max_delay=3.0,
            jitter=0.1
        ),
        powershell={
            "path": os.environ.get("POWERSHELL_PATH", ""),  # 環境変数から取得
            "args": ["-NoProfile", "-ExecutionPolicy", "Bypass"],
            "encoding": "utf-8",
            "init_command": "$OutputEncoding = [System.Text.Encoding]::UTF8; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Output 'SESSION_READY'"
        }
    )

@pytest_asyncio.fixture
async def session(session_config: PowerShellControllerSettings) -> AsyncGenerator[PowerShellSession, None]:
    """テスト用のPowerShellSessionインスタンスを提供するフィクスチャ"""
    if USE_MOCK:
        mock_session = AsyncMock(spec=PowerShellSession)
        mock_session.execute.side_effect = async_mock_execute
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_session.process = mock_process
        yield mock_session
        await mock_session.cleanup()
    else:
        session = PowerShellSession(settings=session_config)
        try:
            async with session:
                yield session
        except Exception as e:
            logger.error(f"セッション作成中にエラーが発生: {e}")
            raise
        finally:
            # 確実にセッションをクリーンアップ
            try:
                await session.cleanup()
            except Exception as e:
                logger.error(f"セッションクリーンアップ中にエラーが発生: {e}")

async def async_mock_execute(command: str) -> str:
    """モック用の非同期execute関数"""
    if "Write-Output" in command:
        # 出力コマンドの場合、引用符内のテキストを抽出
        match = re.search(r"Write-Output\s+'([^']*)'", command)
        if match:
            return match.group(1)
        match = re.search(r"Write-Output\s+\"([^\"]*)\"", command)
        if match:
            return match.group(1)
        return "Output"
    elif "Get-NonExistentCommand" in command or "Get-NonExistentCmdlet" in command:
        # 存在しないコマンドの場合、例外を発生
        from powershell_controller.core.errors import PowerShellExecutionError
        raise PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized.", details=command)
    elif "Start-Sleep" in command:
        # スリープコマンドの場合、タイムアウト例外を発生
        if "-Seconds 5" in command:
            from powershell_controller.core.errors import PowerShellTimeoutError
            raise PowerShellTimeoutError("Operation timed out")
        # 短いスリープは普通に成功
        return "Sleep completed"
    elif "ConvertTo-Json" in command or "JSON" in command.upper():
        # JSON関連のコマンド
        if "PSCustomObject" in command:
            return '{"Name":"Test","Value":123}'
        elif "[1, 2, 3]" in command:
            return '[1,2,3]'
        return '{}'
    else:
        # その他のコマンドはただ成功
        return "Command executed successfully"

@pytest.fixture
def controller_config():
    """テスト用のコントローラー設定"""
    return PowerShellControllerSettings(
        log_level="DEBUG",
        timeouts=TimeoutConfig(
            default=60.0,    # タイムアウトを大幅に延長
            startup=60.0,    # 初期化タイムアウトを大幅に延長
            execution=15.0   # 実行タイムアウトを延長
        ),
        retry=RetryConfig(
            max_attempts=3,  # リトライ回数を増やす
            base_delay=0.3,
            max_delay=3.0,
            jitter=0.1
        ),
        powershell={
            "encoding": "utf-8",
            "init_command": "$ErrorActionPreference='Stop'; $OutputEncoding = [System.Text.Encoding]::UTF8; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Output 'SESSION_READY'"
        }
    )

@pytest_asyncio.fixture
async def mock_session() -> AsyncGenerator[AsyncMock, None]:
    """モック化されたPowerShellSessionを提供するフィクスチャ"""
    # セッションをモック化
    mock_session = AsyncMock(spec=PowerShellSession)
    
    # executeメソッドのモック実装
    async def mock_execute(command: str) -> str:
        if "Write-Output" in command:
            # 出力コマンドの場合、引用符内のテキストを抽出
            match = re.search(r"Write-Output\s+'([^']*)'", command)
            if match:
                return match.group(1)
            match = re.search(r"Write-Output\s+\"([^\"]*)\"", command)
            if match:
                return match.group(1)
            return "Output"
        elif "Get-NonExistentCommand" in command or "Get-NonExistentCmdlet" in command:
            # 存在しないコマンドの場合、例外を発生
            from powershell_controller.core.errors import PowerShellExecutionError
            raise PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized.", details=command)
        elif "Start-Sleep" in command:
            # スリープコマンドの場合、タイムアウト例外を発生
            if "-Seconds 5" in command:
                from powershell_controller.core.errors import PowerShellTimeoutError
                raise PowerShellTimeoutError("Operation timed out")
            # 短いスリープは普通に成功
            return "Sleep completed"
        elif "ConvertTo-Json" in command or "JSON" in command.upper():
            # JSON関連のコマンド
            if "PSCustomObject" in command:
                return '{"Name":"Test","Value":123}'
            elif "[1, 2, 3]" in command:
                return '[1,2,3]'
            return '{}'
        elif "$env:" in command:
            # 環境変数関連のコマンド
            if "=" in command:  # 設定
                return ""
            else:  # 取得
                return "test_value"
        elif "@(1, 2, 3)" in command:
            # 配列を返すコマンド
            return "[1,2,3]"
        elif "1..100" in command:
            # 大量出力テスト
            return "\n".join([f"Line {i}" for i in range(1, 101)])
        elif "$var =" in command or "$var +=" in command:
            # 変数操作
            return ""
        elif ";" in command:
            # 複数のコマンドを含む場合
            return "複数コマンド実行完了"
        elif "Test-ConnectionFailed" in command:
            # 通信エラーのシミュレーション
            from powershell_controller.core.errors import CommunicationError
            raise CommunicationError("通信エラーが発生しました")
        elif "Test-ProcessFailed" in command:
            # プロセスエラーのシミュレーション
            from powershell_controller.core.errors import ProcessError
            raise ProcessError("プロセスが予期せず終了しました")
        elif "Get-Date" in command:
            # 日付コマンド
            return "2025-05-07 12:00:00"
        else:
            # その他のコマンドはただ成功
            return "Command executed successfully"
    
    # モックメソッドを設定
    mock_session.execute.side_effect = mock_execute
    
    # プロセス関連の属性をモック化
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_session.process = mock_process
    
    yield mock_session
    
    # クリーンアップメソッドのモック
    mock_session.cleanup = AsyncMock()
    await mock_session.cleanup()

@pytest.fixture
def use_mock_sessions(monkeypatch):
    """テスト全体でPowerShellSessionをモック化する"""
    # ユーザー指定のモック設定があれば、それを尊重
    if not USE_MOCK and "POWERSHELL_TEST_MOCK" not in os.environ:
        logger.info("モックを使用せずに実際のテストを実行します")
        return

    # モック化する
    logger.info("PowerShellセッションをモック化します")
    
    # PowerShellSessionの__aenter__をパッチ
    async def mock_aenter(self):
        # モック化したプロセス属性を設定
        self.process = MagicMock()
        self.process.pid = 12345
        return self
        
    # executeメソッドをパッチ
    async def mock_execute(self, command: str) -> str:
        if "Write-Output" in command:
            # 出力コマンドの場合、引用符内のテキストを抽出
            match = re.search(r"Write-Output\s+'([^']*)'", command)
            if match:
                return match.group(1)
            match = re.search(r"Write-Output\s+\"([^\"]*)\"", command)
            if match:
                return match.group(1)
            return "Output"
        elif "Get-NonExistentCommand" in command or "Get-NonExistentCmdlet" in command:
            # 存在しないコマンドの場合、例外を発生
            from powershell_controller.core.errors import PowerShellExecutionError
            raise PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized.", details=command)
        elif "Start-Sleep" in command:
            # スリープコマンドの場合、タイムアウト例外を発生
            if "-Seconds 5" in command:
                from powershell_controller.core.errors import PowerShellTimeoutError
                raise PowerShellTimeoutError("Operation timed out")
            # 短いスリープは普通に成功
            return "Sleep completed"
        elif "ConvertTo-Json" in command or "JSON" in command.upper():
            # JSON関連のコマンド
            if "PSCustomObject" in command:
                return '{"Name":"Test","Value":123}'
            elif "[1, 2, 3]" in command:
                return '[1,2,3]'
            return '{}'
        elif "$env:" in command:
            # 環境変数関連のコマンド
            if "=" in command:  # 設定
                return ""
            else:  # 取得
                return "test_value"
        elif "@(1, 2, 3)" in command:
            # 配列を返すコマンド
            return "[1,2,3]"
        elif "$var =" in command or "$var +=" in command:
            # 変数操作
            return ""
        elif ";" in command:
            # 複数のコマンドを含む場合
            return "複数コマンド実行完了"
        elif "Test-ConnectionFailed" in command:
            # 通信エラーのシミュレーション
            from powershell_controller.core.errors import CommunicationError
            raise CommunicationError("通信エラーが発生しました")
        elif "Test-ProcessFailed" in command:
            # プロセスエラーのシミュレーション
            from powershell_controller.core.errors import ProcessError
            raise ProcessError("プロセスが予期せず終了しました")
        elif "Get-Date" in command:
            # 日付コマンド
            return "2025-05-07 12:00:00"
        else:
            # その他のコマンドはただ成功
            return "Command executed successfully"
    
    async def mock_run_command(self, command: str) -> CommandResult:
        """SimplePowerShellControllerのrun_commandメソッドをモック化"""
        if "Write-Output" in command:
            # 出力コマンドの場合、引用符内のテキストを抽出
            match = re.search(r"Write-Output\s+'([^']*)'", command)
            if match:
                return CommandResult(output=match.group(1), success=True)
            match = re.search(r"Write-Output\s+\"([^\"]*)\"", command)
            if match:
                return CommandResult(output=match.group(1), success=True)
            return CommandResult(output="Output", success=True)
        elif "Get-NonExistentCommand" in command or "Get-NonExistentCmdlet" in command:
            # 存在しないコマンドの場合はエラー
            return CommandResult(
                output="", 
                error="CommandNotFound: The term 'Get-NonExistentCommand' is not recognized.", 
                success=False, 
                details={"error_type": "execution_error", "command": command}
            )
        elif "Start-Sleep" in command:
            # スリープコマンドの場合
            if "-Seconds 5" in command:
                return CommandResult(
                    output="", 
                    error="Operation timed out", 
                    success=False, 
                    details={"error_type": "timeout_error", "command": command}
                )
            # 短いスリープは普通に成功
            return CommandResult(output="Sleep completed", success=True)
        elif "Test-ConnectionFailed" in command:
            # 通信エラーのシミュレーション
            return CommandResult(
                output="", 
                error="通信エラーが発生しました", 
                success=False, 
                details={"error_type": "communication_error", "command": command}
            )
        elif "Test-ProcessFailed" in command:
            # プロセスエラーのシミュレーション
            return CommandResult(
                output="", 
                error="プロセスが予期せず終了しました", 
                success=False, 
                details={"error_type": "process_error", "command": command}
            )
        elif "Get-Date" in command:
            # 日付コマンド
            return CommandResult(output="2025-05-07 12:00:00", success=True)
        else:
            # その他のコマンドはただ成功
            return CommandResult(output="Command executed successfully", success=True)

    async def mock_close(self) -> None:
        # 何もしない
        pass
    
    monkeypatch.setattr(PowerShellSession, "__aenter__", mock_aenter)
    monkeypatch.setattr(PowerShellSession, "execute", mock_execute)
    monkeypatch.setattr(PowerShellSession, "cleanup", AsyncMock())
    
    # SimplePowerShellControllerもモック化
    from powershell_controller.simple import SimplePowerShellController
    monkeypatch.setattr(SimplePowerShellController, "run_command", mock_run_command)
    monkeypatch.setattr(SimplePowerShellController, "close", mock_close)
    
    # execute_command_resultをモック化
    def mock_execute_command_result(self, command: str):
        from result import Ok, Err
        from powershell_controller.core.errors import PowerShellExecutionError
        
        if "Get-NonExistentCommand" in command:
            return Err(PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized."))
        elif "Write-Output" in command:
            match = re.search(r"Write-Output\s+'([^']*)'", command)
            if match:
                return Ok(match.group(1))
            match = re.search(r"Write-Output\s+\"([^\"]*)\"", command)
            if match:
                return Ok(match.group(1))
            return Ok("Output")
        else:
            return Ok("Command executed successfully")
    
    # execute_commands_in_session_resultをモック化
    def mock_execute_commands_in_session_result(self, commands: list):
        from result import Ok, Err
        from powershell_controller.core.errors import PowerShellExecutionError
        
        if any("Get-NonExistentCommand" in cmd for cmd in commands):
            return Err(PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized."))
        
        results = []
        for cmd in commands:
            if "Write-Output" in cmd:
                match = re.search(r"Write-Output\s+'([^']*)'", cmd)
                if match:
                    results.append(match.group(1))
                    continue
                match = re.search(r"Write-Output\s+\"([^\"]*)\"", cmd)
                if match:
                    results.append(match.group(1))
                    continue
                results.append("Output")
            else:
                results.append("Command executed successfully")
        return Ok(results)
    
    monkeypatch.setattr(SimplePowerShellController, "execute_command_result", mock_execute_command_result)
    monkeypatch.setattr(SimplePowerShellController, "execute_commands_in_session_result", mock_execute_commands_in_session_result)
    monkeypatch.setattr(SimplePowerShellController, "execute_script_result", mock_execute_command_result) 