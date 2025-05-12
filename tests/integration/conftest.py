"""
PowerShellテスト用の共通フィクスチャ（統合テスト用）
"""
import asyncio
import os
import re
import subprocess
import sys
import threading
import time
from typing import AsyncGenerator, Dict, List, Optional, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from loguru import logger

from py_pshell.config import PowerShellControllerSettings, PowerShellTimeoutSettings
from py_pshell.controller import PowerShellController
from py_pshell.utils.command_result import CommandResult
from py_pshell.errors import (
    CommunicationError,
    PowerShellError,
    PowerShellExecutionError,
    PowerShellTimeoutError,
    ProcessError,
)
from py_pshell.session import PowerShellSession

# テスト環境の情報
IS_WINDOWS = sys.platform.lower() == "win32"
IS_CI = "CI" in os.environ
USE_MOCK = os.environ.get("POWERSHELL_TEST_MOCK", "true").lower() == "true"

@pytest.fixture(scope="session")
def event_loop_policy():
    """イベントループポリシーを設定するフィクスチャ"""
    if IS_WINDOWS:
        # Windowsの場合、ProactorEventLoopを使用
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.get_event_loop_policy()

# event_loopフィクスチャは pytest_asyncio が自動的に提供

@pytest.fixture
def session_config() -> PowerShellControllerSettings:
    """テスト用のPowerShellセッション設定を提供します。"""
    # デフォルト設定を使用するが、タイムアウトは短くしてテストを高速化
    timeout_settings = PowerShellTimeoutSettings(
        startup=5.0,  # 起動タイムアウト
        shutdown=2.0,  # シャットダウンタイムアウト
        default=2.0,   # デフォルトのコマンドタイムアウト
    )
    
    settings = PowerShellControllerSettings(
        powershell_executable="powershell" if IS_WINDOWS else "pwsh",
        timeout=timeout_settings,
        encoding="utf-8",
        use_custom_host=True,
        debug=True,
    )
    
    # CIモードでの設定調整
    if IS_CI:
        # CI環境ではさらにタイムアウトを長めに設定（不安定性に対処）
        settings.timeout.startup = 10.0
        settings.timeout.shutdown = 5.0
        settings.timeout.default = 5.0
    
    return settings

@pytest_asyncio.fixture
async def session(session_config: PowerShellControllerSettings) -> AsyncGenerator[PowerShellSession, None]:
    """実際のPowerShellセッションを提供します。
    
    このフィクスチャはリアルなPowerShellセッションを作成します。
    mock_sessionでモック化されたセッションを使用する場合は、このフィクスチャを使用しないでください。
    """
    if USE_MOCK:
        pytest.skip("モック使用が有効なため、実際のセッションを使用するテストをスキップします")
        
    session = PowerShellSession(settings=session_config)
    await session.__aenter__()
    yield session
    await session.__aexit__(None, None, None)

async def async_mock_execute(command: str) -> str:
    """PowerShellコマンドの実行をモック化する関数
    
    この関数はasyncioベースのモック実装を提供します。
    """
    # 簡単なコマンド解析
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
        # スリープコマンドの場合、実際に少し待機
        match = re.search(r"-Seconds\s+(\d+)", command)
        if match and int(match.group(1)) > 1:
            raise PowerShellTimeoutError("Operation timed out")
        # 短いスリープは普通に成功
        return "Sleep completed"
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
    
    monkeypatch.setattr(PowerShellController, "run_command", mock_run_command)
    monkeypatch.setattr(PowerShellController, "execute_command", mock_execute_command) 