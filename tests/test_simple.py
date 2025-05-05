"""
PowerShell Controllerのテストスイート
"""
import subprocess
import time
import os
import sys
import tempfile
import json
from loguru import logger
import pytest
from powershell_controller.simple import (
    SimplePowerShellController,
    PowerShellError,
    PowerShellExecutionError,
    PowerShellTimeoutError,
    PowerShellControllerConfig,
    RetryConfig
)

# テスト用の定数
TEST_PS_PATH = r"C:\Program Files\PowerShell\7\pwsh.exe"

@pytest.fixture
def mock_process_factory(mocker):
    """プロセスモックのファクトリを提供するフィクスチャ"""
    def create_mock(stdout="", stderr="", returncode=0, timeout=None):
        process = mocker.Mock()
        
        def communicate(*args, **kwargs):
            if timeout is not None and kwargs.get('timeout', 0) < timeout:
                raise subprocess.TimeoutExpired(["test"], kwargs.get('timeout', 0))
            return stdout, stderr
        
        process.communicate = communicate
        process.returncode = returncode
        process.kill = mocker.Mock()
        return process
    
    return create_mock

@pytest.fixture
def mock_popen(mocker, mock_process_factory):
    """subprocess.Popenをモック化するフィクスチャ"""
    def popen_side_effect(*args, **kwargs):
        if "Write-Output 'PowerShell 7 Test'" in args[0][4]:
            return mock_process_factory("PowerShell 7 Test")
        elif "Start-Sleep" in args[0][4]:
            return mock_process_factory(timeout=10)
        elif "throw" in args[0][4]:
            return mock_process_factory(stderr="ERROR_TYPE: RuntimeException\nERROR_MESSAGE: Test Error", returncode=1)
        elif "network error" in args[0][4]:
            return mock_process_factory(stderr="ERROR_TYPE: RuntimeException\nERROR_MESSAGE: network error", returncode=2)
        else:
            return mock_process_factory()
    
    popen_mock = mocker.patch("subprocess.Popen", side_effect=popen_side_effect)
    return popen_mock

@pytest.fixture
def controller_config():
    """テスト用のコントローラー設定を提供するフィクスチャ"""
    return PowerShellControllerConfig(
        log_level="DEBUG",
        retry_config=RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=0.3,
            jitter=0.05
        )
    )

@pytest.fixture
def controller(controller_config):
    """テスト用のPowerShellControllerインスタンスを提供するフィクスチャ"""
    return SimplePowerShellController(config=controller_config)

class TestPowerShellController:
    """PowerShellControllerのテストクラス"""
    
    def test_successful_command(self, controller):
        """正常なコマンド実行のテスト"""
        result = controller.execute_command("Write-Output 'Test'")
        assert result.strip() == "Test"

    def test_timeout_error(self, controller):
        """タイムアウトエラーのテスト"""
        with pytest.raises(PowerShellTimeoutError) as exc_info:
            controller.execute_command("Start-Sleep -Seconds 10", timeout=1)
        assert "timed out" in str(exc_info.value)

    def test_execution_error(self, controller):
        """実行エラーのテスト"""
        with pytest.raises(PowerShellExecutionError) as exc_info:
            controller.execute_command("throw 'Test Error'")
        assert "Test Error" in str(exc_info.value)

    def test_retryable_error(self, controller):
        """リトライ可能なエラーのテスト"""
        with pytest.raises(PowerShellExecutionError) as exc_info:
            controller.execute_command("Write-Error 'network error'")
        assert "network error" in str(exc_info.value)
        assert "retries" in str(exc_info.value)

    def test_json_output(self, controller, mock_process_factory, mock_popen):
        """JSON出力のテスト"""
        json_output = """
        JSON_START
        {"Name": "Test", "Value": 123, "Array": [1, 2, 3]}
        JSON_END
        """
        mock_popen.side_effect = lambda *args, **kwargs: mock_process_factory(json_output)
        
        result = controller.execute_command("@{Name='Test'; Value=123; Array=@(1,2,3)} | ConvertTo-Json")
        assert isinstance(result, dict)
        assert result["Name"] == "Test"
        assert result["Value"] == 123
        assert result["Array"] == [1, 2, 3]

    def test_multiple_commands(self, controller):
        """複数コマンドの実行テスト"""
        commands = [
            "Write-Output 'First'",
            "Write-Output 'Second'"
        ]
        results = controller.execute_commands_in_session(commands)
        assert len(results) == 2
        assert results[0] == "First"
        assert results[1] == "Second"

if __name__ == '__main__':
    pytest.main() 