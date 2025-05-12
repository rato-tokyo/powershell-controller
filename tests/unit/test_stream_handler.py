"""
StreamHandlerのテスト

StreamHandlerクラスの機能テスト
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from py_pshell.config import PowerShellControllerSettings, PowerShellTimeoutSettings
from py_pshell.errors import PowerShellExecutionError
from py_pshell.stream_handler import StreamHandler


class TestStreamHandler:
    """StreamHandlerクラスのテスト"""

    @pytest.fixture
    def mock_reader(self):
        """モックの標準出力ストリーム"""
        reader = AsyncMock(spec=asyncio.StreamReader)
        # 注意: AsyncMockはデフォルトで非同期コルーチンを返すので、
        # サイドエフェクトには直接bytesオブジェクトではなく、
        # コルーチンをシミュレートするためにbytesを返す関数を設定する
        async def read_side_effect(*args, **kwargs):
            result = reader._mock_data.pop(0)
            return result

        reader.read = AsyncMock(side_effect=read_side_effect)
        reader._mock_data = []  # テスト時にこのリストにデータを設定する
        return reader

    @pytest.fixture
    def mock_writer(self):
        """モックの標準入力ストリーム"""
        writer = AsyncMock(spec=asyncio.StreamWriter)
        writer.write = MagicMock()  # 非同期でない関数
        writer.drain = AsyncMock()
        writer.close = MagicMock()  # 非同期でない関数
        writer.wait_closed = AsyncMock()
        return writer

    @pytest.fixture
    def settings(self):
        """テスト用の設定"""
        settings = PowerShellControllerSettings(
            powershell_executable="powershell",
            encoding="utf-8",
            debug=True,
            timeout_settings=PowerShellTimeoutSettings(default=30.0)
        )
        return settings

    @pytest.fixture
    def stream_handler(self, settings, mock_reader, mock_writer):
        """テスト用のStreamHandler"""
        handler = StreamHandler(settings)
        handler.set_streams(mock_reader, mock_writer)
        # タイムアウト設定の参照を修正するためにモンキーパッチを適用
        with patch.object(handler, 'settings') as mock_settings:
            mock_settings.timeout_settings.default = 30.0
            mock_settings.encoding = settings.encoding
            yield handler

    @pytest.mark.asyncio
    async def test_initialize(self, stream_handler, mock_writer):
        """初期化処理のテスト"""
        # モックの準備
        mock_writer.write.reset_mock()
        mock_writer.drain.reset_mock()

        # 初期化を実行
        await stream_handler.initialize()

        # 初期化コマンドが送信されたことを確認
        mock_writer.write.assert_called()
        mock_writer.drain.assert_called()

    @pytest.mark.asyncio
    async def test_send_command(self, stream_handler, mock_writer):
        """コマンド送信のテスト"""
        command = "Get-Process"
        
        # コマンドを送信
        await stream_handler.send_command(command)
        
        # コマンドが正しく書き込まれたか確認
        mock_writer.write.assert_called()
        mock_writer.drain.assert_called()

    @pytest.mark.asyncio
    async def test_read_output(self, stream_handler, mock_reader):
        """出力読み取りのテスト"""
        # モックの設定
        mock_reader._mock_data = [
            b"Process1",
            b"Process2",
            b"Done",
            b"",  # ストリーム終了
        ]
        
        # wait_forをパッチしてasyncio.wait_forの動作をシミュレート
        async def mock_wait_for(coro, timeout):
            return await coro
            
        # 出力を読み取り
        with patch("asyncio.wait_for", side_effect=mock_wait_for):
            output = await stream_handler.read_output()
            
            # 出力が正しく結合されているか確認
            assert "Process1Process2Done" in output

    @pytest.mark.asyncio
    async def test_execute_command_success(self, stream_handler):
        """コマンド実行成功のテスト"""
        command = "Get-Process"
        expected_output = "Process1\nProcess2"
        
        # モックメソッドのパッチ
        stream_handler.send_command = AsyncMock()
        stream_handler.read_output = AsyncMock(return_value=expected_output)
        
        # コマンド実行
        with patch.object(stream_handler, 'settings'):
            output = await stream_handler.execute_command(command)
        
            # 出力が正しいか確認
            assert output == expected_output
            stream_handler.send_command.assert_called_once_with(command)
            stream_handler.read_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_command_with_error(self, stream_handler):
        """エラーが発生するコマンド実行のテスト"""
        command = "Invalid-Command"
        
        # モックメソッドのパッチ
        stream_handler.send_command = AsyncMock()
        stream_handler.read_output = AsyncMock(return_value="エラーCOMMAND_ERROR")
        
        # 例外が発生するか確認
        with pytest.raises(PowerShellExecutionError):
            await stream_handler.execute_command(command)
        
        # メソッドが正しく呼ばれたか確認
        stream_handler.send_command.assert_called_once_with(command)
        stream_handler.read_output.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, stream_handler, mock_writer):
        """ストリームクローズのテスト"""
        # ストリームを閉じる
        await stream_handler.close()
        
        # close()とwait_closed()が呼ばれたか確認
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_encoding_errors(self, settings):
        """エンコーディングエラー処理のテスト"""
        # UTF-8以外のエンコーディングを設定
        settings.encoding = "shift-jis"
        
        # モックリーダーの作成
        mock_reader = AsyncMock(spec=asyncio.StreamReader)
        
        # 読み取りメソッドをオーバーライド
        async def read_side_effect(*args, **kwargs):
            result = mock_reader._mock_data.pop(0)
            return result
            
        mock_reader.read = AsyncMock(side_effect=read_side_effect)
        mock_reader._mock_data = [
            "こんにちは".encode("shift-jis"),
            "世界".encode("shift-jis"),
            b"",  # ストリーム終了
        ]
        
        mock_writer = AsyncMock(spec=asyncio.StreamWriter)
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        
        # StreamHandlerを作成
        handler = StreamHandler(settings)
        handler.set_streams(mock_reader, mock_writer)
        
        # asyncio.wait_forをモック
        async def mock_wait_for(coro, timeout):
            return await coro
            
        # 出力を読み取り
        with patch("asyncio.wait_for", side_effect=mock_wait_for), \
             patch.object(handler, 'settings') as mock_settings:
            mock_settings.timeout_settings.default = 30.0
            mock_settings.encoding = "shift-jis"
            
            output = await handler.read_output()
            
            # 日本語が正しく処理されたか確認
            assert "こんにちは" in output
            assert "世界" in output 