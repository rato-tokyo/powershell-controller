"""
CommandExecutorのテスト

CommandExecutorクラスの機能テスト
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from py_pshell.command_executor import CommandExecutor
from py_pshell.errors import PowerShellError, PowerShellExecutionError


class TestCommandExecutor:
    """CommandExecutorクラスのテスト"""

    @pytest.fixture
    def mock_session(self):
        """モックセッションを作成するフィクスチャ"""
        session = AsyncMock()
        # 標準的な実行パターンを定義
        session.execute.return_value = "成功"
        return session

    @pytest.mark.asyncio
    async def test_run_command_success(self, mock_session):
        """コマンド実行の成功テスト"""
        executor = CommandExecutor(mock_session)
        command = "Get-Process"
        mock_session.execute.return_value = "process1\nprocess2"

        result = await executor.run_command(command)

        # セッションのexecuteが正しく呼び出されたか
        mock_session.execute.assert_called_once_with(command, None)
        # 結果が正しいか
        assert result.output == "process1\nprocess2"
        assert result.error == ""
        assert result.success is True
        assert result.command == command
        assert result.execution_time >= 0

    @pytest.mark.asyncio
    async def test_run_command_powershell_error(self, mock_session):
        """PowerShellエラー発生時のテスト"""
        executor = CommandExecutor(mock_session)
        command = "Invalid-Command"
        error_message = "PowerShellエラーが発生しました"
        mock_session.execute.side_effect = PowerShellError(error_message)

        result = await executor.run_command(command)

        # エラー処理が正しく行われたか
        assert result.output == ""
        assert result.error == error_message
        assert result.success is False
        assert result.command == command
        assert result.execution_time >= 0

    @pytest.mark.asyncio
    async def test_run_command_generic_exception(self, mock_session):
        """一般的な例外発生時のテスト"""
        executor = CommandExecutor(mock_session)
        command = "Test-Command"
        mock_session.execute.side_effect = ValueError("一般的なエラーが発生しました")

        result = await executor.run_command(command)

        # 例外が処理され、適切な結果が返されたか
        assert result.output == ""
        assert "予期しないエラー" in result.error
        assert result.success is False
        assert result.command == command
        assert result.execution_time >= 0

    @pytest.mark.asyncio
    async def test_run_script(self, mock_session):
        """スクリプト実行のテスト"""
        executor = CommandExecutor(mock_session)
        script = "$var = 1; Write-Output $var"
        mock_session.execute.return_value = "1"

        result = await executor.run_script(script)

        # スクリプトが正しく実行されたか
        mock_session.execute.assert_called_once_with(script, None)
        assert result.output == "1"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_command_success(self, mock_session):
        """execute_commandの成功テスト"""
        executor = CommandExecutor(mock_session)
        command = "Get-Service"
        mock_session.execute.return_value = "service1\nservice2"

        result = await executor.execute_command(command)

        # 結果が文字列として返されるか
        assert result == "service1\nservice2"
        mock_session.execute.assert_called_once_with(command, None)

    @pytest.mark.asyncio
    async def test_execute_command_error(self, mock_session):
        """execute_commandのエラーテスト"""
        executor = CommandExecutor(mock_session)
        command = "Invalid-Service"
        mock_session.execute.side_effect = Exception("エラーが発生しました")

        # 例外が発生するか
        with pytest.raises(PowerShellExecutionError):
            await executor.execute_command(command)

    @pytest.mark.asyncio
    async def test_run_command_with_timeout(self, mock_session):
        """タイムアウト指定のテスト"""
        executor = CommandExecutor(mock_session)
        command = "Long-Command"
        timeout = 10.0

        await executor.run_command(command, timeout)

        # タイムアウトが正しく渡されたか
        mock_session.execute.assert_called_once_with(command, timeout)

    def test_get_or_create_loop(self, mock_session):
        """イベントループ作成のテスト"""
        # 実行中のループがない状態をモック
        with patch("asyncio.get_running_loop", side_effect=RuntimeError), patch(
            "threading.Thread"
        ) as mock_thread:

            # 新しいループを作成
            mock_loop = MagicMock()
            mock_loop.is_closed.return_value = False

            with patch("asyncio.new_event_loop", return_value=mock_loop):
                executor = CommandExecutor(mock_session)

                # 初回呼び出し
                loop1 = executor._get_or_create_loop()

                # イベントループが作成されたか
                assert loop1 == mock_loop
                mock_thread.assert_called_once()

                # 2回目の呼び出し - 既存のループを再利用するはず
                loop2 = executor._get_or_create_loop()

                # 同じループが返されるか
                assert loop2 == mock_loop
                # スレッドは1回だけ作成されるはず
                assert mock_thread.call_count == 1
