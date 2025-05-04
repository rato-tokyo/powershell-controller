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
import json
import structlog
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
        """テストの前準備"""
        # テスト用の一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.temp_log_path = os.path.join(self.temp_dir, 'test.log')
        
        # 既存のロガーをクリーンアップ
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # テスト用のメモリログハンドラー
        self.memory_handler = structlog.testing.LogCapture()
        
        # コントローラーの初期化
        self.controller = SimplePowerShellController(
            log_level=logging.DEBUG,
            log_file=self.temp_log_path,
            test_handler=self.memory_handler
        )
        
        # ログの初期化を待機
        time.sleep(0.5)
        
        # ログファイルが存在することを確認
        self.assertTrue(os.path.exists(self.temp_log_path), "ログファイルが作成されていません")
        
        # ログファイルサイズが0より大きいことを確認
        file_size = os.path.getsize(self.temp_log_path)
        self.assertGreater(file_size, 0, f"ログファイルが空です: {self.temp_log_path}, サイズ: {file_size}バイト")

    def tearDown(self):
        """テストの後片付け"""
        try:
            # コントローラーのクリーンアップ
            if hasattr(self, 'controller'):
                # ロガーのハンドラーをクリーンアップ
                logger = logging.getLogger()
                for handler in logger.handlers[:]:
                    try:
                        handler.flush()
                        handler.close()
                    except Exception:
                        pass
                    finally:
                        logger.removeHandler(handler)
                
                # プロセスのクリーンアップ
                self.controller._cleanup_process()
                
                # 参照を削除
                del self.controller
            
            # 一時ディレクトリとログファイルの削除を試みる
            time.sleep(0.5)  # ファイルロックが解除されるのを待つ
            
            try:
                if os.path.exists(self.temp_log_path):
                    os.unlink(self.temp_log_path)
                if os.path.exists(self.temp_dir):
                    os.rmdir(self.temp_dir)
            except (PermissionError, OSError) as e:
                print(f"Warning: Failed to cleanup test files: {e}")
                
        except Exception as e:
            print(f"Warning: Error during teardown: {e}")

    def test_basic_command(self):
        """基本的なコマンド実行のテスト"""
        result = self.controller.execute_command("Write-Output 'Test'")
        self.assertEqual(result.strip(), "Test")
        
        # ログの確認
        self.assertTrue(
            any(
                event.get("event") == "command_execution_complete"
                for event in self.memory_handler.entries
            )
        )

    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        with self.assertRaises(PowerShellExecutionError) as context:
            self.controller.execute_command("throw 'Test Error'")
        self.assertIn("Test Error", str(context.exception))
        
        # エラーログの確認
        self.assertTrue(
            any(
                event.get("event") == "command_execution_failed"
                and "Test Error" in str(event.get("error", ""))
                for event in self.memory_handler.entries
            )
        )

    def test_timeout_handling(self):
        """タイムアウト処理のテスト"""
        with self.assertRaises(PowerShellTimeoutError):
            self.controller.execute_command("Start-Sleep -Seconds 10", timeout=1)
        
        # タイムアウトログの確認
        self.assertTrue(
            any(
                "timeout" in str(event.get("event", ""))
                for event in self.memory_handler.entries
            )
        )

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
        
        # クリーンアップログの確認
        self.assertTrue(
            any(
                event.get("event") == "process_cleanup_complete"
                for event in self.memory_handler.entries
            )
        )

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
        
        # セッション実行ログの確認
        self.assertTrue(
            any(
                event.get("event") == "session_execution_complete"
                for event in self.memory_handler.entries
            )
        )

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
        
        # エラーログの確認
        self.assertTrue(
            any(
                event.get("event") == "command_execution_error"
                and "Test Error" in str(event.get("error", ""))
                for event in self.memory_handler.entries
            )
        )

    def test_utf8_output(self):
        """UTF-8出力のテスト"""
        japanese_text = "こんにちは、世界！"
        result = self.controller.execute_command(f"Write-Output '{japanese_text}'")
        self.assertEqual(result.strip(), japanese_text)

    def test_logging(self):
        """ロギング機能のテスト"""
        # コマンドを実行してログを生成
        test_command = "Write-Output 'Logging Test'"
        self.controller.execute_command(test_command)
        
        # ログファイルの書き込みを待機
        max_retries = 10
        retry_delay = 0.5
        log_lines = []
        
        for i in range(max_retries):
            time.sleep(retry_delay)
            try:
                with open(self.temp_log_path, 'r', encoding='utf-8') as f:
                    log_lines = [line.strip() for line in f.readlines() if line.strip()]
                if log_lines:
                    break
            except Exception as e:
                print(f"Retry {i+1}/{max_retries}: Failed to read log file: {e}")
        
        # ログファイルが存在し、内容があることを確認
        self.assertTrue(os.path.exists(self.temp_log_path), "ログファイルが存在しません")
        self.assertTrue(log_lines, f"ログファイルが空です: {self.temp_log_path}")
        
        # デバッグ用にログ内容を出力
        print("\nLog file contents:")
        for line in log_lines:
            print(f"  {line}")
            
        # 各ログエントリがJSON形式であることを確認
        parsed_logs = []
        for line in log_lines:
            try:
                log_entry = json.loads(line)
                self.assertIsInstance(log_entry, dict)
                self.assertIn("event", log_entry)
                parsed_logs.append(log_entry)
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON format in log line: {line}")
                print(f"Error: {e}")
                continue
        
        # ログエントリが存在することを確認
        self.assertTrue(parsed_logs, "有効なログエントリがありません")
        
        # ログイベントを取得
        log_events = [log.get("event") for log in parsed_logs]
        print("\nFound log events:", log_events)
        
        # いずれかのイベントが存在することを確認する緩和されたチェック
        self.assertTrue(log_events, "ログイベントが存在しません")
        
        # 必要なイベントタイプが存在することを確認
        required_event_types = ["command_execution_start", "command_execution_complete"]
        found_event_types = set(log_events)
        
        for event_type in required_event_types:
            self.assertIn(
                event_type, 
                found_event_types, 
                f"必要なイベント '{event_type}' がログに記録されていません。記録されたイベント: {found_event_types}"
            )
        
        # ロギングが機能していることの確認は完了

    def test_object_output(self):
        """PowerShellオブジェクトの出力テスト"""
        # PowerShellオブジェクトを返すコマンド
        command = """
        @{
            Name = 'TestObject'
            Value = 123
            Data = @{
                Type = 'Test'
                Items = @('A', 'B', 'C')
            }
        }
        """
        result = self.controller.execute_command(command)
        
        # JSON形式で返されることを確認
        data = json.loads(result)
        self.assertEqual(data["Name"], "TestObject")
        self.assertEqual(data["Value"], 123)
        self.assertEqual(data["Data"]["Type"], "Test")
        self.assertEqual(data["Data"]["Items"], ["A", "B", "C"])

if __name__ == '__main__':
    unittest.main() 