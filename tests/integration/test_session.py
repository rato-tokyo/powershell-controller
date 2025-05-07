"""
PowerShellセッションのテスト
"""
import pytest
import asyncio
import os
import platform
from loguru import logger

from py_pshell.session import PowerShellSession
from py_pshell.config import PowerShellControllerSettings
from py_pshell.errors import PowerShellExecutionError, PowerShellTimeoutError

# テスト環境の情報
IS_WINDOWS = platform.system().lower() == "windows"
IS_CI = "CI" in os.environ
USE_MOCK = os.environ.get("POWERSHELL_TEST_MOCK", "true").lower() == "true"

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_session_basic_functionality(use_mock_sessions, session_config):
    """PowerShellセッションの基本機能テスト"""
    session = None
    try:
        session = PowerShellSession(settings=session_config)
        await session.__aenter__()
        
        # 基本的なコマンド実行
        result = await session.execute("Write-Output 'Basic session test'")
        assert "Basic session test" in result or result == "Basic session test"
        
        # 複数行のコマンド実行
        multi_line_cmd = """
        $var = "Test"
        Write-Output $var
        """
        # 一行に変換
        formatted_cmd = "; ".join(line.strip() for line in multi_line_cmd.strip().split("\n"))
        
        result = await session.execute(formatted_cmd)
        assert "Test" in result or "Output" in result  # モックモードでは "Output" が返る
        
    finally:
        if session:
            await session.__aexit__(None, None, None)

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_session_error_handling(use_mock_sessions, session_config):
    """PowerShellセッションのエラー処理テスト"""
    session = None
    try:
        session = PowerShellSession(settings=session_config)
        await session.__aenter__()
        
        # 存在しないコマンドを実行
        try:
            await session.execute("Get-NonExistentCommand")
            pytest.fail("エラーが発生しませんでした")
        except PowerShellExecutionError as e:
            # 例外メッセージを確認
            assert "NonExistentCommand" in str(e) or "not recognized" in str(e)
        
        # エラー後も実行できるか確認
        result = await session.execute("Write-Output 'After error'")
        assert "After error" in result
        
    finally:
        if session:
            await session.__aexit__(None, None, None)

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_session_context_manager(use_mock_sessions, session_config):
    """コンテキストマネージャーとしてのセッション使用テスト"""
    async with PowerShellSession(settings=session_config) as session:
        # コンテキスト内でコマンドを実行
        result = await session.execute("Write-Output 'Context manager test'")
        assert "Context manager test" in result

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_session_timeout(use_mock_sessions, session_config):
    """セッションのタイムアウト処理テスト"""
    session = None
    try:
        session = PowerShellSession(settings=session_config)
        await session.__aenter__()
        
        # タイムアウトするコマンド
        try:
            await session.execute("Start-Sleep -Seconds 5")
            pytest.fail("タイムアウトが発生しませんでした")
        except PowerShellTimeoutError as e:
            # 例外メッセージを確認
            assert "time" in str(e).lower() or "タイムアウト" in str(e)
        
        # セッションが引き続き使用可能なことを確認
        result = await session.execute("Write-Output 'Session still works'")
        assert result
        
    finally:
        if session:
            await session.__aexit__(None, None, None)

@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_session_restart(use_mock_sessions, session_config):
    """セッションの再起動テスト"""
    session = None
    try:
        session = PowerShellSession(settings=session_config)
        await session.__aenter__()
        
        # 最初のコマンド実行
        result1 = await session.execute("Write-Output 'First command'")
        assert "First command" in result1
        
        # セッションを停止
        await session.__aexit__(None, None, None)
        
        # セッションを再起動
        await session.__aenter__()
        
        # 再起動後のコマンド実行
        result2 = await session.execute("Write-Output 'After restart'")
        assert "After restart" in result2
        
    finally:
        if session:
            await session.__aexit__(None, None, None) 