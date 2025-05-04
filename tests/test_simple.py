"""
PowerShell Controllerの簡易テスト
"""
import subprocess
import time
import os
import sys
import unittest
import psutil
import logging
import tempfile
from src.powershell_controller.simple import (
    SimplePowerShellController,
    PowerShellError,
    PowerShellExecutionError,
    PowerShellTimeoutError
)

def test_direct_powershell_command():
    """PowerShellコマンドが直接実行できることを確認"""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Write-Output 'Hello from PowerShell'"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert "Hello from PowerShell" in result.stdout
        assert result.returncode == 0
    except subprocess.TimeoutExpired:
        assert False, "PowerShellコマンドがタイムアウトしました"
    except Exception as e:
        assert False, f"エラーが発生しました: {e}"

def test_powershell7_availability():
    """PowerShell 7が利用可能かチェック"""
    ps7_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
    
    # PowerShell 7が存在するか
    assert os.path.exists(ps7_path), "PowerShell 7が見つかりません"
    
    # 実行して出力を確認
    try:
        result = subprocess.run(
            [ps7_path, "-Command", "Write-Output 'Hello from PowerShell 7'"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert "Hello from PowerShell 7" in result.stdout
        assert result.returncode == 0
    except subprocess.TimeoutExpired:
        assert False, "PowerShell 7のコマンドがタイムアウトしました"
    except Exception as e:
        assert False, f"エラーが発生しました: {e}"

class TestSimplePowerShellController(unittest.TestCase):
    def setUp(self):
        # テスト用の一時ログファイルを作成
        self.temp_log = tempfile.NamedTemporaryFile(suffix='.log', delete=False)
        self.temp_log.close()
        
        self.controller = SimplePowerShellController(
            log_level=logging.DEBUG,
            log_file=self.temp_log.name
        )

    def tearDown(self):
        # 一時ログファイルを削除
        if os.path.exists(self.temp_log.name):
            os.unlink(self.temp_log.name)

    def test_basic_command(self):
        """基本的なコマンド実行のテスト"""
        result = self.controller.execute_command("Write-Output 'Test'")
        self.assertEqual(result.strip(), "Test")

    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        with self.assertRaises(PowerShellExecutionError) as context:
            self.controller.execute_command("throw 'Test Error'")
        self.assertIn("Test Error", str(context.exception))

    def test_timeout_handling(self):
        """タイムアウト処理のテスト"""
        with self.assertRaises(PowerShellTimeoutError):
            self.controller.execute_command("Start-Sleep -Seconds 10", timeout=1)

    def test_process_cleanup(self):
        """プロセスのクリーンアップが正しく動作することを確認"""
        # 長時間実行されるコマンドを開始
        with self.assertRaises(PowerShellTimeoutError):
            self.controller.execute_command("Start-Sleep -Seconds 30", timeout=1)
        
        # プロセスが正しく終了されていることを確認
        self.assertIsNone(self.controller.pid)
        self.assertIsNone(self.controller.process)
        
        # 元のプロセスとその子プロセスが存在しないことを確認
        if self.controller.pid is not None:
            with self.assertRaises(psutil.NoSuchProcess):
                psutil.Process(self.controller.pid)

    def test_multiple_commands(self):
        """複数コマンドの実行とプロセス管理を確認"""
        commands = [
            "Write-Output 'Command 1'",
            "Write-Output 'Command 2'",
            "Write-Output 'Command 3'"
        ]
        results = self.controller.execute_commands_in_session(commands)
        
        # 結果を確認
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].strip(), "Command 1")
        self.assertEqual(results[1].strip(), "Command 2")
        self.assertEqual(results[2].strip(), "Command 3")
        
        # プロセスが正しくクリーンアップされていることを確認
        self.assertIsNone(self.controller.pid)
        self.assertIsNone(self.controller.process)

    def test_multiple_commands_with_error(self):
        """エラーを含む複数コマンドの実行テスト"""
        commands = [
            "Write-Output 'Success 1'",
            "throw 'Test Error'",
            "Write-Output 'Success 2'"
        ]
        results = self.controller.execute_commands_in_session(commands)
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].strip(), "Success 1")
        self.assertIn("Test Error", results[1])
        self.assertEqual(results[2].strip(), "Success 2")

    def test_utf8_output(self):
        """UTF-8出力のテスト"""
        japanese_text = "こんにちは、世界！"
        result = self.controller.execute_command(f"Write-Output '{japanese_text}'")
        self.assertEqual(result.strip(), japanese_text)

    def test_logging(self):
        """ロギング機能のテスト"""
        # コマンドを実行してログを生成
        self.controller.execute_command("Write-Output 'Logging Test'")
        
        # ログファイルの内容を確認
        with open(self.temp_log.name, 'r', encoding='utf-8') as f:
            log_content = f.read()
            
        # 必要なログエントリが存在することを確認
        self.assertIn("コマンド実行開始", log_content)
        self.assertIn("プロセス開始", log_content)
        self.assertIn("コマンド実行完了", log_content)

if __name__ == '__main__':
    unittest.main() 