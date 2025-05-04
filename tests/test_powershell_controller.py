"""
PowerShell Controllerのテストコード
"""
import pytest
import os
from src.powershell_controller.controller import PowerShellController

class TestPowerShellController:
    @pytest.fixture
    def controller(self):
        """テスト用のコントローラーインスタンスを提供します"""
        controller = PowerShellController()
        yield controller
        controller.close()

    def test_powershell_session_starts(self, controller):
        """PowerShellセッションが正常に開始できることをテスト"""
        assert controller.process is not None
        assert controller.process.poll() is None  # プロセスが実行中であることを確認

    def test_execute_simple_command(self, controller):
        """単純なコマンドを実行できることをテスト"""
        result = controller.execute_command("Write-Output 'Hello, PowerShell!'")
        assert "Hello, PowerShell!" in result

    def test_maintain_session_state(self, controller):
        """セッション状態が維持されることをテスト"""
        # 変数を設定
        controller.execute_command("$test_var = 'test_value'")
        # 変数の値を取得
        result = controller.execute_command("Write-Output $test_var")
        assert "test_value" in result

    def test_directory_navigation(self, controller):
        """ディレクトリ移動が正常に動作することをテスト"""
        # 現在のディレクトリを保存
        initial_dir = controller.execute_command("$PWD.Path").strip()
        
        # 1階層上に移動
        controller.execute_command("cd ..")
        new_dir = controller.execute_command("$PWD.Path").strip()
        
        # パスが変更されていることを確認
        assert initial_dir != new_dir
        assert len(initial_dir) > len(new_dir)
        
        # 元のディレクトリに戻る
        controller.execute_command(f"cd '{initial_dir}'")
        current_dir = controller.execute_command("$PWD.Path").strip()
        assert current_dir == initial_dir

    def test_error_handling(self, controller):
        """エラーハンドリングが正常に動作することをテスト"""
        with pytest.raises(Exception):
            controller.execute_command("NonExistentCommand")

    def test_command_output_special_chars(self, controller):
        """特殊文字を含む出力の処理をテスト"""
        special_chars = "!@#$%^&*()_+{}[]|\\:;\"'<>,.?/~`"
        result = controller.execute_command(f"Write-Output '{special_chars}'")
        assert special_chars in result

    def test_multiple_line_output(self, controller):
        """複数行の出力を正しく処理できることをテスト"""
        command = """
        Write-Output 'Line 1'
        Write-Output 'Line 2'
        Write-Output 'Line 3'
        """
        result = controller.execute_command(command)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_session_cleanup(self, controller):
        """セッションが正しくクリーンアップされることをテスト"""
        process = controller.process
        controller.close()
        assert process.poll() is not None  # プロセスが終了していることを確認

    def test_large_output_handling(self, controller):
        """大量の出力を正しく処理できることをテスト"""
        # 1000行の出力を生成
        command = "1..1000 | ForEach-Object { Write-Output \"Line $_\" }"
        result = controller.execute_command(command)
        assert "Line 1" in result
        assert "Line 1000" in result
        
    def test_background_jobs(self, controller):
        """バックグラウンドジョブの処理をテスト"""
        # バックグラウンドジョブを開始
        controller.execute_command("Start-Job -ScriptBlock { Start-Sleep -Seconds 2; Write-Output 'Job Complete' }")
        # ジョブの完了を待機
        result = controller.execute_command("Wait-Job | Receive-Job")
        assert "Job Complete" in result 