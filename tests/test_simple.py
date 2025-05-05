"""
PowerShell Controllerのテストスイート
"""
import os
import subprocess
from typing import Any, Callable, Optional

import pytest
from deepdiff import DeepDiff

from powershell_controller.simple import (
    PowerShellControllerSettings,
    PowerShellExecutionError,
    PowerShellTimeoutError,
    RetryConfig,
    SimplePowerShellController,
)

# テスト用の定数
TEST_PS_PATH = r"C:\Program Files\PowerShell\7\pwsh.exe"

@pytest.fixture
def mock_process_factory(mocker: Any) -> Callable[..., Any]:
    """プロセスモックのファクトリを提供するフィクスチャ"""
    def create_mock(
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
        timeout: Optional[float] = None
    ) -> Any:
        process = mocker.Mock()
        
        def communicate(*args: Any, **kwargs: Any) -> tuple[str, str]:
            if timeout is not None and kwargs.get('timeout', 0) < timeout:
                raise subprocess.TimeoutExpired(["test"], kwargs.get('timeout', 0))
            return stdout, stderr
        
        process.communicate = communicate
        process.returncode = returncode
        process.kill = mocker.Mock()
        return process
    
    return create_mock

@pytest.fixture
def mock_popen(mocker: Any, mock_process_factory: Callable[..., Any]) -> Any:
    """subprocess.Popenをモック化するフィクスチャ"""
    def popen_side_effect(*args: Any, **kwargs: Any) -> Any:
        if "Write-Output 'PowerShell 7 Test'" in args[0][4]:
            return mock_process_factory("PowerShell 7 Test")
        elif "Start-Sleep" in args[0][4]:
            return mock_process_factory(timeout=10)
        elif "throw" in args[0][4]:
            return mock_process_factory(
                stderr="ERROR_TYPE: RuntimeException\nERROR_MESSAGE: Test Error",
                returncode=1
            )
        elif "network error" in args[0][4]:
            return mock_process_factory(
                stderr="ERROR_TYPE: RuntimeException\nERROR_MESSAGE: network error",
                returncode=2
            )
        else:
            return mock_process_factory()
    
    popen_mock = mocker.patch("subprocess.Popen", side_effect=popen_side_effect)
    return popen_mock

@pytest.fixture
def controller_config() -> PowerShellControllerSettings:
    """テスト用のコントローラー設定を提供するフィクスチャ"""
    return PowerShellControllerSettings(
        log_level="DEBUG",
        retry_config=RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=0.3,
            jitter=0.05
        )
    )

@pytest.fixture
def controller(controller_config: PowerShellControllerSettings) -> SimplePowerShellController:
    """テスト用のPowerShellControllerインスタンスを提供するフィクスチャ"""
    return SimplePowerShellController(config=controller_config)

class TestPowerShellController:
    """PowerShellControllerのテストクラス"""
    
    def test_successful_command(self, controller: SimplePowerShellController) -> None:
        """正常なコマンド実行のテスト"""
        result = controller.execute_command("Write-Output 'Test'")
        assert result.strip() == "Test"

    def test_timeout_error(self, controller: SimplePowerShellController) -> None:
        """タイムアウトエラーのテスト"""
        with pytest.raises(PowerShellTimeoutError) as exc_info:
            controller.execute_command("Start-Sleep -Seconds 10", timeout=1)
        assert "timed out" in str(exc_info.value)

    def test_execution_error(self, controller: SimplePowerShellController) -> None:
        """実行エラーのテスト"""
        with pytest.raises(PowerShellExecutionError) as exc_info:
            controller.execute_command("throw 'Test Error'")
        assert "Test Error" in str(exc_info.value)

    def test_retryable_error(self, controller: SimplePowerShellController) -> None:
        """リトライ可能なエラーのテスト"""
        with pytest.raises(PowerShellExecutionError) as exc_info:
            controller.execute_command("Write-Error 'network error'")
        assert "network error" in str(exc_info.value)
        assert "retries" in str(exc_info.value)

    def test_json_output(
        self,
        controller: SimplePowerShellController,
        mock_process_factory: Callable[..., Any],
        mock_popen: Any
    ) -> None:
        """JSON出力のテスト"""
        json_output = """
        JSON_START
        {"Name": "Test", "Value": 123, "Array": [1, 2, 3]}
        JSON_END
        """
        mock_popen.side_effect = lambda *args, **kwargs: mock_process_factory(json_output)
        
        cmd = "@{Name='Test'; Value=123; Array=@(1,2,3)} | ConvertTo-Json"
        result = controller.execute_command(cmd)
        assert isinstance(result, dict)
        assert result["Name"] == "Test"
        assert result["Value"] == 123
        assert result["Array"] == [1, 2, 3]

    def test_multiple_commands(self, controller: SimplePowerShellController) -> None:
        """複数コマンドの実行テスト"""
        commands = [
            "Write-Output 'First'",
            "Write-Output 'Second'"
        ]
        results = controller.execute_commands_in_session(commands)
        assert len(results) == 2
        assert results[0] == "First"
        assert results[1] == "Second"

def test_controller_initialization() -> None:
    """コントローラーの初期化テスト"""
    controller = SimplePowerShellController()
    assert controller is not None
    assert controller.config is not None

def test_controller_with_env_vars(monkeypatch: Any) -> None:
    """環境変数からの設定読み込みテスト"""
    # 環境変数を設定
    monkeypatch.setenv("PS_CTRL_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PS_CTRL_LOG_FILE", "test.log")
    
    controller = SimplePowerShellController()
    assert controller.config.log_level == "DEBUG"
    assert controller.config.log_file == "test.log"

def test_execute_command_success() -> None:
    """基本的なコマンド実行テスト"""
    controller = SimplePowerShellController()
    result = controller.execute_command("Write-Output 'test'")
    assert result == "test"

def test_execute_command_json_output() -> None:
    """JSON出力を返すコマンドのテスト"""
    controller = SimplePowerShellController()
    result = controller.execute_command("@{ 'key' = 'value'; 'nested' = @{ 'inner' = 'data' } }")
    expected = {
        "key": "value",
        "nested": {
            "inner": "data"
        }
    }
    # deepdiffを使用して構造化データを比較
    diff = DeepDiff(result, expected, ignore_order=True)
    assert not diff, f"Unexpected differences found: {diff}"

def test_execute_command_error() -> None:
    """エラーを発生させるコマンドのテスト"""
    controller = SimplePowerShellController()
    with pytest.raises(PowerShellExecutionError):
        controller.execute_command("throw 'Test error'")

def test_execute_command_timeout() -> None:
    """タイムアウトのテスト"""
    controller = SimplePowerShellController()
    with pytest.raises(PowerShellTimeoutError):
        controller.execute_command("Start-Sleep -Seconds 5", timeout=1)

def test_execute_commands_in_session() -> None:
    """セッション内での複数コマンド実行テスト"""
    controller = SimplePowerShellController()
    commands = [
        "Write-Output 'test1'",
        "Write-Output 'test2'"
    ]
    results = controller.execute_commands_in_session(commands)
    assert len(results) == 2
    assert results[0] == "test1"
    assert results[1] == "test2"

def test_execute_script() -> None:
    """スクリプト実行テスト"""
    controller = SimplePowerShellController()
    script = """
    $result = "test script"
    Write-Output $result
    """
    result = controller.execute_script(script)
    assert result == "test script"

def test_complex_json_output() -> None:
    """複雑なJSON出力を返すコマンドのテスト"""
    controller = SimplePowerShellController()
    result = controller.execute_command("""
        @{
            'array' = @(1, 2, 3);
            'nested' = @{
                'list' = @('a', 'b', 'c');
                'dict' = @{ 'x' = 1; 'y' = 2 }
            }
        }
    """)
    expected = {
        "array": [1, 2, 3],
        "nested": {
            "list": ["a", "b", "c"],
            "dict": {"x": 1, "y": 2}
        }
    }
    # deepdiffを使用して複雑な構造を比較
    diff = DeepDiff(result, expected, ignore_order=True)
    assert not diff, f"Unexpected differences found: {diff}"

if __name__ == '__main__':
    pytest.main() 