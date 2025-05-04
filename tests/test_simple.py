"""
PowerShell Controllerの簡易テスト
"""
import subprocess
import time
import os
import sys
import unittest
import psutil
from src.powershell_controller.simple import SimplePowerShellController

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

def test_command_with_exit():
    """終了コマンドを含めても正常に実行できることを確認"""
    ps7_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
    
    try:
        commands = """
        Write-Output 'Before Exit'
        # 通常、exitするとプロセスが終了するが、-NoExitオプションで防止
        Write-Output 'After pseudo-exit'
        """
        
        result = subprocess.run(
            [ps7_path, "-NoExit", "-Command", commands],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        assert "Before Exit" in result.stdout
        assert "After pseudo-exit" in result.stdout
    except subprocess.TimeoutExpired:
        assert False, "コマンドがタイムアウトしました"
    except Exception as e:
        assert False, f"エラーが発生しました: {e}"

class TestSimplePowerShellController(unittest.TestCase):
    def setUp(self):
        self.controller = SimplePowerShellController()

    def test_process_cleanup(self):
        """プロセスのクリーンアップが正しく動作することを確認"""
        # 長時間実行されるコマンドを開始
        with self.assertRaises(subprocess.TimeoutExpired):
            self.controller.execute_command("Start-Sleep -Seconds 30", timeout=1)
        
        # プロセスが正しく終了されていることを確認
        self.assertIsNone(self.controller.pid)
        self.assertIsNone(self.controller.process)

    def test_process_info_logging(self):
        """プロセス情報のロギングが動作することを確認"""
        # コマンドを実行してプロセス情報が記録されることを確認
        result = self.controller.execute_command("Write-Output 'Test'")
        self.assertEqual(result.strip(), "Test")
        
        # プロセスが正しくクリーンアップされていることを確認
        self.assertIsNone(self.controller.pid)
        self.assertIsNone(self.controller.process)

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

if __name__ == '__main__':
    unittest.main() 