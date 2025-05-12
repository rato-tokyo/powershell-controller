"""
ProcessManagerのテスト

ProcessManagerクラスの機能テスト
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from py_pshell.config import PowerShellControllerSettings
from py_pshell.errors import PowerShellShutdownError, PowerShellStartupError
from py_pshell.process_manager import ProcessManager


class TestProcessManager:
    """ProcessManagerクラスのテスト"""

    @pytest.fixture
    def settings(self):
        """テスト用の設定"""
        return PowerShellControllerSettings(
            powershell_executable="powershell" if sys.platform.lower() == "win32" else "pwsh",
            encoding="utf-8",
            debug=True,
        )

    @pytest.fixture
    def process_manager(self, settings):
        """テスト用のProcessManager"""
        return ProcessManager(settings)

    @pytest.mark.asyncio
    async def test_start(self, process_manager):
        """プロセス作成のテスト"""
        # モックプロセスとストリームを作成
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.stdout = MagicMock()
        mock_process.stdin = MagicMock()
        
        mock_reader = MagicMock(spec=asyncio.StreamReader)
        mock_writer = MagicMock(spec=asyncio.StreamWriter)
        
        # startメソッド内で呼び出される関数をモック
        with patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("asyncio.get_running_loop"), \
             patch("asyncio.StreamReader", return_value=mock_reader), \
             patch("asyncio.StreamReaderProtocol"), \
             patch("asyncio.StreamWriter", return_value=mock_writer), \
             patch("asyncio.wait_for", return_value=mock_process):
            
            # プロセスを起動
            reader, writer = await process_manager.start()
            
            # プロセスとストリームが設定されたか確認
            assert process_manager._process == mock_process
            assert reader == mock_reader
            assert writer == mock_writer

    @pytest.mark.asyncio
    async def test_start_error(self, process_manager):
        """プロセス作成エラーのテスト"""
        # タイムアウトエラーをシミュレート
        async def mock_wait_for(*args, **kwargs):
            raise TimeoutError("プロセスの起動がタイムアウトしました")
            
        # 例外が発生するようにモック
        with patch("asyncio.wait_for", side_effect=mock_wait_for):
            # エラーが発生するか確認
            with pytest.raises(PowerShellStartupError):
                await process_manager.start()

    @pytest.mark.asyncio
    async def test_stop(self, process_manager):
        """プロセス終了のテスト"""
        # モックプロセスを作成
        mock_process = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()
        
        # モックストリームを作成
        mock_writer = MagicMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()
        
        # プロセスとストリームを設定
        process_manager._process = mock_process
        process_manager._writer = mock_writer
        
        # プロセスを終了
        await process_manager.stop()
        
        # プロセスが終了されたか確認
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        
        # ストリームが閉じられたか確認
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()
        
        # プロセスの参照がクリアされたか確認
        assert process_manager._process is None
        assert process_manager._writer is None

    @pytest.mark.asyncio
    async def test_stop_no_process(self, process_manager):
        """プロセスがない場合の終了処理テスト"""
        # プロセスが設定されていない状態
        process_manager._process = None
        process_manager._writer = None
        
        # 例外が発生しないことを確認
        await process_manager.stop()

    @pytest.mark.asyncio
    async def test_stop_error(self, process_manager):
        """プロセス終了時のエラーテスト"""
        # 例外を発生させるモックプロセス
        mock_process = MagicMock()
        error_msg = "プロセスが見つかりません"
        mock_process.terminate = MagicMock(side_effect=ProcessLookupError(error_msg))
        mock_process.wait = AsyncMock()
        
        # プロセスを設定
        process_manager._process = mock_process
        
        # 例外が発生するか確認
        with pytest.raises(PowerShellShutdownError):
            await process_manager.stop()

    def test_is_running_true(self, process_manager):
        """プロセス実行中の判定テスト"""
        # 実行中のプロセスをモック
        mock_process = MagicMock()
        mock_process.returncode = None
        
        # プロセスを設定
        process_manager._process = mock_process
        
        # 実行中と判定されるか確認
        assert process_manager.is_running is True

    def test_is_running_false(self, process_manager):
        """プロセス終了時の判定テスト"""
        # 終了したプロセスをモック
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        # プロセスを設定
        process_manager._process = mock_process
        
        # 終了と判定されるか確認
        assert process_manager.is_running is False
        
        # プロセスが設定されていない場合
        process_manager._process = None
        
        # 終了と判定されるか確認
        assert process_manager.is_running is False 