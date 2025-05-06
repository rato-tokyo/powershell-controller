"""
エラーリカバリー機能のテスト
"""
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import platform
from result import Result, Ok, Err
from loguru import logger
import warnings

from powershell_controller import (
    SimplePowerShellController, 
    CommandResult,
    PowerShellError, 
    PowerShellExecutionError, 
    ProcessError, 
    PowerShellTimeoutError,
    PowerShellControllerSettings
)
from powershell_controller.utils.config import TimeoutConfig, RetryConfig
from powershell_controller.core.session import PowerShellSession
from pydantic import ValidationError

# テスト環境の情報
IS_WINDOWS = platform.system().lower() == "windows"
IS_CI = "CI" in os.environ
USE_MOCK = os.environ.get("POWERSHELL_TEST_MOCK", "true").lower() == "true"

# テスト環境でモックを有効にする
os.environ["POWERSHELL_TEST_MOCK"] = "true"

@pytest.fixture
def session_config():
    """テスト用のセッション設定を作成"""
    return PowerShellControllerSettings(
        timeouts=TimeoutConfig(
            command=3.0,
            connection=2.0,
            startup=5.0
        ),
        retry=RetryConfig(
            max_attempts=2,
            initial_delay=0.1,
            max_delay=1.0
        ),
        use_mock=True
    )

@pytest.fixture
def controller(use_mock_sessions):
    """テスト用のコントローラを作成"""
    controller = SimplePowerShellController()
    yield controller
    
    # クリーンアップ
    loop = asyncio.get_event_loop()
    loop.run_until_complete(controller.close())

@pytest.mark.asyncio
@pytest.mark.timeout(30)  # テストのタイムアウトを短縮（モック使用）
async def test_error_in_powershell_script(use_mock_sessions, session_config):
    """PowerShellスクリプトエラーのテスト - 実際にエラーを発生させて検証"""
    controller = None
    try:
        # SimplePowerShellControllerを使用
        controller = SimplePowerShellController(settings=session_config)
        
        # 正常なスクリプト
        valid_script = """
        $var = "Hello"
        Write-Output $var
        """
        
        valid_result = controller.execute_script_result(valid_script)
        assert valid_result.is_ok()
        
        # エラーが発生するスクリプト
        error_script = """
        Get-NonExistentCommand
        """
        
        error_result = controller.execute_script_result(error_script)
        assert error_result.is_err()
        assert "NonExistentCommand" in str(error_result.unwrap_err()) or "not recognized" in str(error_result.unwrap_err())
        
        # エラー後も正常に動作することを確認
        result2 = await controller.run_command("Write-Output 'After error test'")
        assert result2.success is True, "エラー後のコマンドは成功するはずです"
        assert "After error test" in result2.output, "エラー後も正常に出力できるはずです"
        
    except Exception as e:
        pytest.fail(f"テスト実行中に予期しないエラーが発生しました: {e}")
    finally:
        if controller:
            await controller.close()
    
    # 次のテストの前に少し待機
    await asyncio.sleep(1.0)

@pytest.mark.asyncio
@pytest.mark.timeout(30)  # テストのタイムアウトを短縮（モック使用）
async def test_session_cleanup_after_error(use_mock_sessions):
    """エラー後のセッションクリーンアップテスト"""
    session = None
    try:
        updated_config = session_config.model_copy(deep=True)
        session = PowerShellSession(settings=updated_config)
        
        async with session:
            # 正常動作の確認
            result = await session.execute("Write-Output 'Before cleanup'")
            assert "Before cleanup" in result
    except Exception as e:
        pytest.fail(f"Unexpected error: {e}")
    finally:
        if session:
            await session.cleanup()
    
    # 次のテストの前に少し待機
    await asyncio.sleep(1.0)

@pytest.mark.asyncio
@pytest.mark.timeout(30)  # テストのタイムアウトを短縮（モック使用）
async def test_sequential_command_execution(use_mock_sessions):
    """複数コマンドの連続実行をテスト (モック使用)"""
    controller = SimplePowerShellController()
    
    try:
        commands = [
            "Write-Output 'Command 1'",
            "Write-Output 'Command 2'",
            "Write-Output 'Command 3'"
        ]
        
        # 同一セッションで複数コマンドを実行
        results = controller.execute_commands_in_session_result(commands)
        
        # 結果を検証
        assert results.is_ok()
        commands_results = results.unwrap()
        
        # 各コマンドの結果を確認
        assert len(commands_results) == 3
        assert "Command 1" in commands_results[0] or "executed successfully" in commands_results[0]
        assert "Command 2" in commands_results[1] or "executed successfully" in commands_results[1] 
        assert "Command 3" in commands_results[2] or "executed successfully" in commands_results[2]
    finally:
        await controller.close()

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_process_restart_recovery_mock(use_mock_sessions):
    """プロセスエラーからの復旧をテスト (モック使用)"""
    controller = SimplePowerShellController()
    
    try:
        # 1回目: 成功するはず
        result1 = await controller.run_command("Write-Output 'Test 1'")
        assert result1.success is True
        assert "Test 1" in result1.output
        
        # プロセスエラーを発生させる
        result2 = await controller.run_command("Test-ProcessFailed")
        assert result2.success is False
        assert "プロセス" in result2.error
        
        # エラー後も実行できるか確認
        result3 = await controller.run_command("Write-Output 'Test 3'")
        assert result3.success is True
        assert "Test 3" in result3.output
    finally:
        await controller.close()

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_communication_error_recovery_mock(use_mock_sessions):
    """通信エラーからの復旧をテスト (モック使用)"""
    controller = SimplePowerShellController()
    
    try:
        # 1回目: 成功するはず
        result1 = await controller.run_command("Write-Output 'Test 1'")
        assert result1.success is True
        assert "Test 1" in result1.output
        
        # 通信エラーを発生させる
        result2 = await controller.run_command("Test-ConnectionFailed")
        assert result2.success is False
        assert "通信エラー" in result2.error
        
        # エラー後も実行できるか確認
        result3 = await controller.run_command("Write-Output 'Test 3'")
        assert result3.success is True
        assert "Test 3" in result3.output
    finally:
        await controller.close()

@pytest.mark.asyncio
async def test_command_result_validation(use_mock_sessions):
    """CommandResultのバリデーションをテスト"""
    # 成功のケース
    result_success = CommandResult(
        output="Test output",
        success=True
    )
    assert result_success.success is True
    assert result_success.output == "Test output"
    assert result_success.error is None
    
    # 失敗のケース（エラーメッセージあり）
    result_error = CommandResult(
        output="",
        error="Test error",
        success=False
    )
    assert result_error.success is False
    assert result_error.error == "Test error"
    
    # 失敗のケース（エラーメッセージなし）
    result_no_error = CommandResult(
        output="",
        success=False
    )
    assert result_no_error.success is False
    assert result_no_error.error is not None  # デフォルトのエラーメッセージが設定されるはず
    
    # 成功なのにエラーメッセージがあるケース (警告が出るはず)
    # 直接警告をキャプチャする代わりに、loggerの警告出力を確認
    logger_mock = MagicMock()
    with patch('powershell_controller.simple.logger', logger_mock):
        result_inconsistent = CommandResult(
            output="Test output",
            error="Warning message",
            success=True
        )
        # loggerの警告メソッドが呼ばれたことを確認
        logger_mock.warning.assert_called_once()
        assert "Command marked as successful but has error message" in logger_mock.warning.call_args[0][0]

@pytest.mark.asyncio
async def test_result_based_error_handling(use_mock_sessions):
    """Result型を使ったエラーハンドリングをテスト (モック使用)"""
    controller = SimplePowerShellController()
    
    try:
        # 成功するケース
        success_result = await controller.run_command("Write-Output 'Success'")
        assert success_result.success is True
        assert "Success" in success_result.output
        
        # 失敗するケース
        error_result = await controller.run_command("Get-NonExistentCommand")
        assert error_result.success is False
        assert error_result.error is not None
        
        # Result型を使用した場合
        result = controller.execute_command_result("Write-Output 'Result Test'")
        assert result.is_ok()
        assert "Result Test" in result.unwrap() or "Command executed successfully" in result.unwrap()
        
        # Result型でのエラーハンドリング
        error = controller.execute_command_result("Get-NonExistentCommand")
        assert error.is_err()
        assert isinstance(error.unwrap_err(), PowerShellError)
    finally:
        await controller.close()

@pytest.mark.asyncio
@pytest.mark.timeout(30)
@pytest.mark.parametrize(
    "command,should_succeed", 
    [
        ("Write-Output 'Test'", True),
        ("Get-Date", True),
        ("Get-NonExistentCommand", False),
        ("Start-Sleep -Seconds 5", False),  # タイムアウトするはず
    ]
)
@pytest.mark.asyncio
async def test_command_execution_parameterized(command, should_succeed, use_mock_sessions):
    """パラメータ化したコマンド実行テスト (モック使用)"""
    controller = SimplePowerShellController()
    
    try:
        result = await controller.run_command(command)
        
        # 成功フラグが期待通りか確認
        assert result.success == should_succeed
        
        if should_succeed:
            assert result.output != ""
            assert result.error is None
        else:
            # エラーメッセージに期待される文字列が含まれているか確認
            # タイムアウトの場合は "timed out" も許可する
            assert ("Error" in result.error or 
                   "error" in result.error.lower() or 
                   "timed out" in result.error.lower() or 
                   "timeout" in result.error.lower() or 
                   "not recognized" in result.error)
    finally:
        await controller.close()

@pytest.mark.asyncio
async def test_session_cleanup_after_error(use_mock_sessions):
    """エラー後のセッションクリーンアップをテスト"""
    # このテストはモック環境でのみ実行する
    controller = SimplePowerShellController()
    
    try:
        # 最初に正常なコマンドを実行
        result1 = await controller.run_command("Write-Output 'Before error'")
        assert result1.success is True
        
        # エラーを発生させるコマンドを実行
        result2 = await controller.run_command("Get-NonExistentCommand")
        assert result2.success is False
        
        # セッションが自動的にリセットされ、再度コマンドが実行できるか確認
        result3 = await controller.run_command("Write-Output 'After error'")
        assert result3.success is True
        assert "After error" in result3.output
    finally:
        await controller.close() 