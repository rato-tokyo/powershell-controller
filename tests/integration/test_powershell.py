"""
PowerShell Controllerの統合テスト
"""
import pytest
import asyncio
from powershell_controller.utils.config import PowerShellControllerSettings, RetryConfig
from powershell_controller.core.errors import PowerShellError, PowerShellTimeoutError, ProcessError
from powershell_controller.core.session.powershell import PowerShellSession
from tenacity import RetryError

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
    
    # PowerShellの例外を正しく処理する必要がある
    async with session:
        try:
            # PowerShellの構文エラーを発生させる (これはリトライされる可能性がある)
            await session.execute("Get-NonExistentCmdlet")
            pytest.fail("エラーが発生しませんでした")
        except RetryError as e:
            # tenacityのRetryErrorから直接最後の例外を取得 
            last_exception = e.last_attempt.exception()
            assert isinstance(last_exception, ProcessError)
            error_msg = str(last_exception)
            assert "NonExistentCmdlet" in error_msg
        except Exception as e:
            # その他の例外が発生した場合
            error_msg = str(e)
            assert "NonExistentCmdlet" in error_msg or "CommandNotFound" in error_msg or "not recognized" in error_msg

@pytest.mark.asyncio
async def test_execute_command_timeout() -> None:
    """タイムアウトのテスト"""
    # タイムアウトを0.1秒に設定し、長時間のスリープを実行
    session = PowerShellSession(timeout=0.1)
    async with session:
        try:
            # 長時間実行されるコマンドを実行
            await session.execute("Start-Sleep -Seconds 10")
            pytest.fail("タイムアウトエラーが発生しませんでした")
        except Exception as e:
            # tenacityのRetryErrorの場合、内部例外を取得
            error_msg = str(e)
            if hasattr(e, "last_attempt"):
                last_attempt = e.last_attempt
                if hasattr(last_attempt, "exception") and last_attempt.exception() is not None:
                    error_msg = str(last_attempt.exception())
            
            # タイムアウトに関するテキストが含まれているか確認
            assert "タイムアウト" in error_msg or "timeout" in error_msg.lower() or "PowerShellTimeoutError" in error_msg

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
        # タイムアウトを0.1秒に設定し、長時間のスリープを実行
        config = controller_config.model_dump()
        session = PowerShellSession(config=config, timeout=0.1)
        async with session:
            try:
                # 長時間実行されるコマンドを実行
                await session.execute("Start-Sleep -Seconds 10")
                pytest.fail("タイムアウトエラーが発生しませんでした")
            except RetryError as e:
                # tenacityのRetryErrorから直接最後の例外を取得
                last_exception = e.last_attempt.exception()
                assert isinstance(last_exception, PowerShellTimeoutError)
                error_msg = str(last_exception)
                assert "timeout" in error_msg.lower() or "タイムアウト" in error_msg
            except Exception as e:
                # その他の例外の場合
                error_msg = str(e)
                assert "タイムアウト" in error_msg or "timeout" in error_msg.lower() or "PowerShellTimeoutError" in error_msg

    @pytest.mark.asyncio
    async def test_execution_error(self, controller_config: PowerShellControllerSettings) -> None:
        """実行エラーのテスト"""
        session = PowerShellSession(config=controller_config.model_dump())
        
        # PowerShellの例外を正しく処理する必要がある
        async with session:
            try:
                # 存在しないコマンド実行でエラーを発生させる
                await session.execute("Get-NonExistentCommand")
                pytest.fail("エラーが発生しませんでした")
            except RetryError as e:
                # tenacityのRetryErrorから直接最後の例外を取得
                last_exception = e.last_attempt.exception()
                assert isinstance(last_exception, ProcessError)
                error_msg = str(last_exception)
                assert "NonExistentCommand" in error_msg
            except Exception as e:
                # その他の例外の場合
                error_msg = str(e)
                assert "NonExistentCommand" in error_msg or "CommandNotFound" in error_msg or "not recognized" in error_msg

    @pytest.mark.asyncio
    async def test_multiple_commands(self, controller_config: PowerShellControllerSettings) -> None:
        """複数コマンドの実行テスト"""
        session = PowerShellSession(config=controller_config.model_dump())
        async with session:
            result1 = await session.execute("Write-Output 'First'")
            result2 = await session.execute("Write-Output 'Second'")
            
        assert result1 == "First"
        assert result2 == "Second" 