"""
PowerShell Controllerの統合テスト
"""
import pytest
import asyncio
from powershell_controller.utils.config import PowerShellControllerSettings, RetryConfig
from powershell_controller.core.errors import PowerShellError, PowerShellTimeoutError, ProcessError
from powershell_controller.core.session.powershell import PowerShellSession

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

@pytest.mark.asyncio
async def test_execute_command_success() -> None:
    """基本的なコマンド実行テスト"""
    session = PowerShellSession()
    async with session:
        result = await session.execute("Write-Output 'test'")
        assert result == "test"

@pytest.mark.asyncio
async def test_execute_command_error() -> None:
    """エラーを発生させるコマンドのテスト"""
    session = PowerShellSession()
    async with session:
        with pytest.raises(ProcessError):
            await session.execute("throw 'Test error'")

@pytest.mark.asyncio
async def test_execute_command_timeout() -> None:
    """タイムアウトのテスト"""
    session = PowerShellSession(timeout=1.0)
    async with session:
        with pytest.raises(PowerShellTimeoutError):
            await session.execute("Start-Sleep -Seconds 5")

@pytest.mark.asyncio
async def test_execute_commands_in_session() -> None:
    """セッション内での複数コマンド実行テスト"""
    session = PowerShellSession()
    async with session:
        result1 = await session.execute("Write-Output 'test1'")
        result2 = await session.execute("Write-Output 'test2'")
        
    assert result1 == "test1"
    assert result2 == "test2"

@pytest.mark.asyncio
async def test_execute_script() -> None:
    """スクリプト実行のテスト"""
    session = PowerShellSession()
    async with session:
        # 複数行のスクリプトを実行
        script = """
        $var = "Hello"
        $var += " World"
        Write-Output $var
        """
        # 複数行のスクリプトはセミコロンで連結
        formatted_script = "; ".join(line.strip() for line in script.strip().split("\n"))
        result = await session.execute(formatted_script)
        assert result == "Hello World"

class TestPowerShellSession:
    """PowerShellSessionの統合テストクラス"""
    
    @pytest.mark.asyncio
    async def test_successful_command(self, controller_config: PowerShellControllerSettings) -> None:
        """正常なコマンド実行のテスト"""
        session = PowerShellSession(config=controller_config.model_dump())
        async with session:
            result = await session.execute("Write-Output 'Test'")
            assert result == "Test"

    @pytest.mark.asyncio
    async def test_timeout_error(self, controller_config: PowerShellControllerSettings) -> None:
        """タイムアウトエラーのテスト"""
        session = PowerShellSession(config=controller_config.model_dump(), timeout=1.0)
        async with session:
            with pytest.raises(PowerShellTimeoutError) as exc_info:
                await session.execute("Start-Sleep -Seconds 10")
            assert "タイムアウト" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execution_error(self, controller_config: PowerShellControllerSettings) -> None:
        """実行エラーのテスト"""
        session = PowerShellSession(config=controller_config.model_dump())
        async with session:
            with pytest.raises(ProcessError) as exc_info:
                await session.execute("throw 'Test Error'")
            assert "エラー" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_multiple_commands(self, controller_config: PowerShellControllerSettings) -> None:
        """複数コマンドの実行テスト"""
        session = PowerShellSession(config=controller_config.model_dump())
        async with session:
            result1 = await session.execute("Write-Output 'First'")
            result2 = await session.execute("Write-Output 'Second'")
            
        assert result1 == "First"
        assert result2 == "Second" 