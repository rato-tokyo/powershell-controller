"""
テスト用の共通フィクスチャーと設定
"""
import os
import re
import pytest
import pytest_asyncio
import platform
import asyncio
from typing import AsyncGenerator, Optional
from unittest.mock import MagicMock, AsyncMock
from contextlib import asynccontextmanager

from loguru import logger

from py_pshell.config import PowerShellControllerSettings
from py_pshell.session import PowerShellSession
from py_pshell.controller import PowerShellController, CommandResult
from py_pshell.errors import PowerShellExecutionError, ProcessError, PowerShellTimeoutError, CommunicationError

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
    from py_pshell.config import PowerShellConfig, TimeoutConfig
    
    # タイムアウト設定を短く
    timeout_config = TimeoutConfig(
        default=5.0,
        startup=5.0,
        execution=5.0,
        shutdown=5.0
    )
    
    # PowerShell固有の設定
    ps_config = PowerShellConfig(
        path="powershell.exe" if platform.system() == "Windows" else "pwsh",
        args=["-NoProfile", "-NoLogo", "-NonInteractive", "-Command", "-"]
    )
    
    # 全体設定
    settings = PowerShellControllerSettings(
        timeout=timeout_config,
        powershell=ps_config,
        log_level="DEBUG",
        use_mock=USE_MOCK
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
        from py_pshell.errors import PowerShellExecutionError
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
            raise PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized.", command)
        elif "Start-Sleep" in command:
            # スリープコマンドの場合、タイムアウト例外を発生
            if "-Seconds 5" in command:
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
        elif "Test-ConnectionFailed" in command:
            # 通信エラーのテスト
            raise CommunicationError("通信エラーが発生しました")
        elif "Test-ProcessFailed" in command:
            # プロセスエラーのテスト
            raise ProcessError("プロセスエラーが発生しました")
        else:
            # その他のコマンドはただ成功
            return "Command executed successfully"

    # PowerShellSessionのモック
    monkeypatch.setattr(PowerShellSession, "__aenter__", mock_aenter)
    monkeypatch.setattr(PowerShellSession, "execute", mock_execute)
    
    # PowerShellControllerのモック
    async def mock_run_command(self, command: str, timeout: Optional[float] = None) -> CommandResult:
        try:
            if not self.session:
                self.session = PowerShellSession(settings=self.settings)
                await self.session.__aenter__()
            
            output = await self.session.execute(command)
            return CommandResult(
                output=output,
                error="",
                success=True,
                command=command,
                execution_time=0.1
            )
        except PowerShellExecutionError as e:
            details = {"error_type": "execution_error"}
            if "not recognized" in str(e) or "CommandNotFound" in str(e):
                details["error_type"] = "command_not_found"
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                command=command,
                execution_time=0.1
            )
        except PowerShellTimeoutError as e:
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                command=command,
                execution_time=0.1
            )
        except CommunicationError as e:
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                command=command,
                execution_time=0.1
            )
        except ProcessError as e:
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                command=command,
                execution_time=0.1
            )
        except Exception as e:
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                command=command,
                execution_time=0.1
            )
    
    def mock_execute_command_result(self, command: str, timeout: Optional[float] = None):
        from result import Ok, Err
        
        try:
            if "Get-NonExistentCommand" in command:
                return Err(PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized."))
            elif "Test-ConnectionFailed" in command:
                return Err(CommunicationError("通信エラーが発生しました"))
            elif "Test-ProcessFailed" in command:
                return Err(ProcessError("プロセスエラーが発生しました"))
            elif "Start-Sleep -Seconds 5" in command:
                return Err(PowerShellTimeoutError("Operation timed out"))
            
            # 正常なコマンドの結果
            if "Write-Output" in command:
                match = re.search(r"Write-Output\s+'([^']*)'", command)
                if match:
                    return Ok(match.group(1))
                return Ok("Output")
            
            return Ok("Command executed successfully")
        except Exception as e:
            return Err(PowerShellError(str(e)))
    
    # モックメソッドをPowerShellControllerに追加
    monkeypatch.setattr(PowerShellController, "run_command", mock_run_command)
    monkeypatch.setattr(PowerShellController, "execute_command_result", mock_execute_command_result)
    
    # execute_commandメソッドもモック化
    def mock_execute_command(self, command: str, timeout: Optional[float] = None) -> str:
        """
        モック化されたexecute_commandメソッド
        """
        try:
            if "Get-NonExistentCommand" in command:
                raise PowerShellExecutionError("CommandNotFound: The term 'Get-NonExistentCommand' is not recognized.")
            elif "Test-ConnectionFailed" in command:
                raise CommunicationError("通信エラーが発生しました")
            elif "Test-ProcessFailed" in command:
                raise ProcessError("プロセスエラーが発生しました")
            elif "Start-Sleep -Seconds 5" in command:
                raise PowerShellTimeoutError("Operation timed out")
                
            # 正常なコマンドの結果
            if "Write-Output" in command:
                match = re.search(r"Write-Output\s+'([^']*)'", command)
                if match:
                    return match.group(1)
                return "Output"
                
            return "Command executed successfully"
        except Exception as e:
            raise PowerShellExecutionError(str(e), command)
    
    monkeypatch.setattr(PowerShellController, "execute_command", mock_execute_command) 