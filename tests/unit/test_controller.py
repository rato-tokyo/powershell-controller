"""
PowerShellコントローラーのテストモジュール

PowerShellコントローラーの機能をテストします。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from py_pshell.controller import PowerShellController
from py_pshell.errors import PowerShellShutdownError, PowerShellStartupError
from py_pshell.interfaces import CommandResultProtocol
from py_pshell.utils.command_result import CommandResult


@pytest_asyncio.fixture
async def controller():
    """PowerShellコントローラーのフィクスチャ"""
    controller = PowerShellController()
    # モックの設定
    controller._session = AsyncMock()
    controller._session.execute = AsyncMock(return_value="Test Output")
    controller._session.stop = AsyncMock()
    controller._command_executor = AsyncMock()
    controller._command_executor.run_command = AsyncMock(
        return_value=CommandResult(
            output="Test Output", error="", success=True, command="Get-Process", execution_time=0.1
        )
    )
    await controller.start()
    yield controller
    await controller.close()


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_context_manager():
    """非同期コンテキストマネージャーのテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    execute_mock = AsyncMock(return_value="Test Output")
    controller._session.execute = execute_mock
    controller._session.stop = AsyncMock()

    async with controller as ctrl:
        assert isinstance(ctrl, PowerShellController)
        result = await ctrl.execute_command("Get-Process")
        assert isinstance(result, str)
        assert result == "Test Output"
        execute_mock.assert_awaited_once_with("Get-Process", None)

    # コンテキストマネージャーを抜けた後の状態を確認
    assert controller._session is None


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_start():
    """startメソッドのテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    controller._session.stop = AsyncMock()
    await controller.start()
    assert controller._session is not None


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_start_error():
    """startメソッドのエラーテスト"""
    controller = PowerShellController()
    controller._session = None
    with pytest.raises(PowerShellStartupError):
        await controller.start()


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_execute_command():
    """コマンド実行のテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    execute_mock = AsyncMock(return_value="Test Output")
    controller._session.execute = execute_mock
    controller._session.stop = AsyncMock()
    await controller.start()

    try:
        result = await controller.execute_command("Get-Process")
        assert isinstance(result, str)
        assert result == "Test Output"
        execute_mock.assert_awaited_once_with("Get-Process", None)
    finally:
        await controller.close()
        assert controller._session is None


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_run_command():
    """run_commandのテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    controller._session.stop = AsyncMock()
    controller._command_executor = AsyncMock()
    controller._command_executor.run_command = AsyncMock(
        return_value=CommandResult(
            output="Test Output", error="", success=True, command="Get-Process", execution_time=0.1
        )
    )
    await controller.start()

    try:
        result = await controller.run_command("Get-Process")
        assert isinstance(result, CommandResultProtocol)
        assert result.success
        assert result.output == "Test Output"
        assert result.error == ""
        assert result.command == "Get-Process"
        assert result.execution_time > 0
    finally:
        await controller.close()
        assert controller._session is None


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_run_script():
    """run_scriptのテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    controller._session.stop = AsyncMock()
    controller._command_executor = AsyncMock()
    expected_result = CommandResult(
        output="Test Output",
        error="",
        success=True,
        command="Get-Process | Select-Object -First 1",
        execution_time=0.1,
    )
    controller._command_executor.run_script = AsyncMock(return_value=expected_result)
    await controller.start()

    try:
        script = "Get-Process | Select-Object -First 1"
        result = await controller.run_script(script)
        assert isinstance(result, CommandResultProtocol)
        assert result.success
        assert result.output == "Test Output"
        assert result.error == ""
        assert result.command == script
        assert result.execution_time > 0
    finally:
        await controller.close()
        assert controller._session is None


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_get_json():
    """JSON取得のテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    execute_mock = AsyncMock(return_value='{"name": "test", "value": 123}')
    controller._session.execute = execute_mock
    controller._session.stop = AsyncMock()
    await controller.start()

    try:
        result = await controller.get_json("Get-Process | Select-Object -First 1 | ConvertTo-Json")
        assert isinstance(result, dict)
        assert result["name"] == "test"
        assert result["value"] == 123
        execute_mock.assert_awaited_once_with(
            "Get-Process | Select-Object -First 1 | ConvertTo-Json", None
        )
    finally:
        await controller.close()
        assert controller._session is None


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_close():
    """closeメソッドのテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    controller._session.stop = AsyncMock()
    await controller.start()
    await controller.close()
    assert controller._session is None


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_close_error():
    """closeメソッドのエラーテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    controller._session.stop = AsyncMock(side_effect=PowerShellShutdownError("Test Error"))
    await controller.start()
    with pytest.raises(PowerShellShutdownError):
        await controller.close()


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_close_sync():
    """close_syncメソッドのテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    controller._session.stop = AsyncMock()

    # イベントループの実行をモック
    mock_loop = MagicMock()
    mock_loop.is_running.return_value = False
    mock_loop.run_until_complete = MagicMock()

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        controller.close_sync()
        assert controller._session is None
        mock_loop.run_until_complete.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.timeout(10)
async def test_close_sync_error():
    """close_syncメソッドのエラーテスト"""
    controller = PowerShellController()
    controller._session = AsyncMock()
    controller._session.stop = AsyncMock(side_effect=PowerShellShutdownError("Test Error"))

    # イベントループの実行をモック
    mock_loop = MagicMock()
    mock_loop.is_running.return_value = False
    mock_loop.run_until_complete = MagicMock(side_effect=PowerShellShutdownError("Test Error"))

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        with pytest.raises(PowerShellShutdownError):
            controller.close_sync()
        assert controller._session is None  # エラーが発生してもセッションはクリーンアップされる
