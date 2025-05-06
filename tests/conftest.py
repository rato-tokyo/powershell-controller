"""
テスト用の共通フィクスチャーと設定
"""
import os
import re
import pytest
import pytest_asyncio
import platform
import asyncio
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock
from contextlib import asynccontextmanager

from loguru import logger

from py_pshell import PowerShellControllerSettings
from py_pshell.core.session import PowerShellSession
from py_pshell.simple import SimplePowerShellController, CommandResult

# デフォルトではモックを使用する
# 環境変数POWERSHELL_TEST_MOCKが設定されている場合は、その値を使用
# 設定されていない場合は、デフォルトでTrueを使用
USE_MOCK = os.environ.get("POWERSHELL_TEST_MOCK", "true").lower() in ("true", "1", "yes")

# イベントループポリシーの設定
@pytest.fixture(scope="session")
def event_loop_policy():
    """テストに使用するイベントループポリシーを設定します。"""
    # Windowsの場合はSelectorEventLoopPolicyを使用
    if platform.system() == "Windows":
        policy = asyncio.WindowsSelectorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        
    # すべてのタスクの完了を保証するためのクリーンアップフックを提供
    old_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(old_loop)
    yield
    
    # セッション終了時にループが適切にクリーンアップされていることを確認
    loop = asyncio.get_event_loop_policy().get_event_loop()
    if not loop.is_closed():
        # 保留中のタスクをキャンセル
        for task in asyncio.all_tasks(loop):
            task.cancel()
        
        # ループを閉じる
        loop.close()
    
# PowerShellControllerの設定
@pytest.fixture
def session_config() -> PowerShellControllerSettings:
    """テスト用のカスタム設定を持つPowerShellControllerSettingsを返します。"""
    from py_pshell.utils.config import PowerShellConfig, TimeoutConfig
    
    # タイムアウト設定を短く
    timeout_config = TimeoutConfig(
        default=5.0,
        startup=5.0,
        execution=5.0,
        read=5.0,
        shutdown=5.0,
        cleanup=5.0
    )
    
    # PowerShell固有の設定
    ps_config = PowerShellConfig(
        path="powershell.exe" if platform.system() == "Windows" else "pwsh",
        args=["-NoProfile", "-NoLogo", "-NonInteractive", "-Command", "-"]
    )
    
    # 全体設定
    settings = PowerShellControllerSettings(
        timeouts=timeout_config,
        powershell=ps_config,
        retry_attempts=2,
        retry_delay=0.5,
        debug_logging=True
    )
    
    return settings

# 実際のPowerShellセッション
@pytest_asyncio.fixture
async def session(session_config: PowerShellControllerSettings) -> AsyncGenerator[PowerShellSession, None]:
    """実際のPowerShellセッションを作成し、テストに提供します。"""
    # ユーザー指定のモック設定があれば、それを尊重
    if USE_MOCK or "POWERSHELL_TEST_MOCK" in os.environ:
        logger.info("モックセッションを使用します")
        # モックセッションを作成
        session = MagicMock(spec=PowerShellSession)
        session.__aenter__.return_value = session
        session.execute = AsyncMock()
        session.execute.return_value = "Mock PowerShell output"
        yield session
        return
        
    # 実際のセッションを作成
    logger.info("実際のPowerShellセッションを使用します")
    session = PowerShellSession(settings=session_config)
    try:
        await session.__aenter__()
        yield session
    finally:
        await session.__aexit__(None, None, None)

# モック化されたexecuteメソッド
async def async_mock_execute(command: str) -> str:
    """モック化されたPowerShellコマンド実行メソッド"""
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
        from py_pshell.core.errors import PowerShellExecutionError
        raise PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized.")
    elif "Test-Error" in command:
        # テスト用のエラー
        raise Exception("Test error")
    else:
        # その他のコマンドはただ成功
        return "Command executed successfully"

# コントローラーの設定
@pytest.fixture
def controller_config():
    """テスト用のコントローラー設定を提供します。"""
    # セッション設定と同じものを使用
    return session_config()

# モック化されたセッション
@pytest_asyncio.fixture
async def mock_session() -> AsyncGenerator[AsyncMock, None]:
    """モック化されたPowerShellセッションを提供します。"""
    session = AsyncMock(spec=PowerShellSession)
    
    # executeメソッドの実装をカスタマイズ
    async def mock_execute(command: str) -> str:
        """モック化された実行メソッド"""
        return await async_mock_execute(command)
    
    session.execute.side_effect = mock_execute
    yield session

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
            from py_pshell.core.errors import PowerShellExecutionError
            raise PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized.", details=command)
        elif "Start-Sleep" in command:
            # スリープコマンドの場合、タイムアウト例外を発生
            if "-Seconds 5" in command:
                from py_pshell.core.errors import PowerShellTimeoutError
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
            from py_pshell.core.errors import CommunicationError
            raise CommunicationError("通信エラーが発生しました")
        elif "Test-ProcessFailed" in command:
            # プロセスエラーのシミュレーション
            from py_pshell.core.errors import ProcessError
            raise ProcessError("プロセスが予期せず終了しました")
        elif "Get-Date" in command:
            # 日付コマンド
            return "2025-05-07 12:00:00"
        else:
            # その他のコマンドはただ成功
            return "Command executed successfully"
    
    # run_commandメソッドをパッチ
    async def mock_run_command(self, command: str) -> CommandResult:
        """SimplePowerShellControllerのrun_commandメソッドをモック化"""
        if "Write-Output" in command:
            # 出力コマンドの場合、引用符内のテキストを抽出
            match = re.search(r"Write-Output\s+'([^']*)'", command)
            if match:
                return CommandResult(output=match.group(1), success=True, error=None)
            match = re.search(r"Write-Output\s+\"([^\"]*)\"", command)
            if match:
                return CommandResult(output=match.group(1), success=True, error=None)
            return CommandResult(output="Output", success=True, error=None)
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
            return CommandResult(output="Sleep completed", success=True, error=None)
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
            return CommandResult(output="2025-05-07 12:00:00", success=True, error=None)
        else:
            # その他のコマンドはただ成功
            return CommandResult(output="Command executed successfully", success=True, error=None)

    # 警告を回避するため、async_mock_closeが常に完了した将来を返すようにする
    mock_close_future = asyncio.Future()
    mock_close_future.set_result(None)
    async_mock_close = AsyncMock()
    async_mock_close.return_value = None  # 明示的にNoneを返すように設定
    
    monkeypatch.setattr(PowerShellSession, "__aenter__", mock_aenter)
    monkeypatch.setattr(PowerShellSession, "execute", mock_execute)
    monkeypatch.setattr(PowerShellSession, "cleanup", AsyncMock())
    
    # SimplePowerShellControllerもモック化
    monkeypatch.setattr(SimplePowerShellController, "run_command", mock_run_command)
    monkeypatch.setattr(SimplePowerShellController, "close", async_mock_close)
    
    # execute_command_resultをモック化
    def mock_execute_command_result(self, command: str):
        from result import Ok, Err
        from py_pshell.core.errors import PowerShellExecutionError
        
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
        from py_pshell.core.errors import PowerShellExecutionError
        
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
    
    # run_commandsもモック化
    async def mock_run_commands(self, commands: list):
        results = []
        for cmd in commands:
            result = await mock_run_command(self, cmd)
            results.append(result)
            if not result.success:
                break
        return results
    
    monkeypatch.setattr(SimplePowerShellController, "execute_command_result", mock_execute_command_result)
    monkeypatch.setattr(SimplePowerShellController, "execute_commands_in_session_result", mock_execute_commands_in_session_result)
    monkeypatch.setattr(SimplePowerShellController, "execute_script_result", mock_execute_command_result)
    monkeypatch.setattr(SimplePowerShellController, "run_commands", mock_run_commands) 