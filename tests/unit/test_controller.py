"""
PowerShellコントローラーのテスト
"""
import pytest
import asyncio
import os
import platform
from loguru import logger

from py_pshell.controller import PowerShellController, CommandResult
from py_pshell.config import PowerShellControllerSettings
from py_pshell.errors import PowerShellError, PowerShellExecutionError, PowerShellTimeoutError

# テスト環境の情報
IS_WINDOWS = platform.system().lower() == "windows"
IS_CI = "CI" in os.environ
USE_MOCK = os.environ.get("POWERSHELL_TEST_MOCK", "true").lower() == "true"

@pytest.fixture
def controller(use_mock_sessions):
    """テスト用のコントローラを作成"""
    controller = PowerShellController()
    yield controller
    
    # クリーンアップ
    loop = asyncio.get_event_loop()
    loop.run_until_complete(controller.close())

@pytest.mark.asyncio
@pytest.mark.timeout(30)  # テストのタイムアウトを短縮（モック使用）
async def test_basic_command_execution(use_mock_sessions):
    """基本的なコマンド実行テスト"""
    controller = None
    try:
        controller = PowerShellController()
        
        # 非同期コマンド実行
        result = await controller.run_command("Write-Output 'Hello, World!'")
        assert result.success is True
        assert result.output == "Hello, World!"
        assert result.error == ""
        assert result.command == "Write-Output 'Hello, World!'"
        assert result.execution_time >= 0
        
        # 同期コマンド実行
        output = controller.execute_command("Write-Output 'Sync test'")
        assert output == "Sync test"
        
    finally:
        if controller:
            await controller.close()

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_error_handling(use_mock_sessions):
    """エラー処理テスト"""
    controller = None
    try:
        controller = PowerShellController()
        
        # 存在しないコマンドを実行
        result = await controller.run_command("Get-NonExistentCommand")
        assert result.success is False
        assert "NonExistentCommand" in result.error or "not recognized" in result.error
        
        # エラー後も正常に実行できることを確認
        result2 = await controller.run_command("Write-Output 'After error'")
        assert result2.success is True
        assert result2.output == "After error"
        
    finally:
        if controller:
            await controller.close()

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_try_except_handling(use_mock_sessions):
    """try-exceptによるエラーハンドリングテスト"""
    controller = None
    try:
        controller = PowerShellController()
        
        # 成功する場合
        output = controller.execute_command("Write-Output 'Success'")
        assert output == "Success"
        
        # 失敗する場合 - 例外がスローされることを確認
        with pytest.raises(PowerShellExecutionError) as excinfo:
            controller.execute_command("Get-NonExistentCommand")
        
        error = excinfo.value
        assert isinstance(error, PowerShellExecutionError)
        assert "NonExistentCommand" in str(error) or "not recognized" in str(error)
        
    finally:
        if controller:
            await controller.close()

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_context_manager(use_mock_sessions):
    """コンテキストマネージャーとしての使用テスト"""
    async with PowerShellController() as controller:
        # コンテキスト内でコマンドを実行
        result = await controller.run_command("Write-Output 'Context test'")
        assert result.success is True
        assert result.output == "Context test"
    
    # コンテキスト終了後はセッションが閉じられているはず

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_timeout_error(use_mock_sessions):
    """タイムアウトエラーのテスト"""
    controller = None
    try:
        controller = PowerShellController()
        
        # タイムアウトするコマンド
        result = await controller.run_command("Start-Sleep -Seconds 5")
        assert result.success is False
        assert "time" in result.error.lower() or "タイムアウト" in result.error
        
        # タイムアウト後も実行できるか確認
        result = await controller.run_command("Write-Output 'After timeout'")
        assert result.success is True
        assert "After timeout" in result.output
        
    finally:
        if controller:
            await controller.close()

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_special_errors(use_mock_sessions):
    """特殊なエラーのテスト"""
    controller = None
    try:
        controller = PowerShellController()
        
        # 通信エラー
        result = await controller.run_command("Test-ConnectionFailed")
        assert result.success is False
        assert "通信エラー" in result.error
        
        # プロセスエラー
        result = await controller.run_command("Test-ProcessFailed")
        assert result.success is False
        assert "プロセスエラー" in result.error or "プロセス" in result.error
        
        # エラー後も正常に実行できることを確認
        result2 = await controller.run_command("Write-Output 'After special error'")
        assert result2.success is True
        assert result2.output == "After special error"
        
    finally:
        if controller:
            await controller.close() 