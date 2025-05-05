"""
テスト用のコンフィギュレーション
"""
import pytest
from typing import Dict, Any, AsyncGenerator
import asyncio
from powershell_controller.core.session import PowerShellSession
from powershell_controller.utils.config import PowerShellControllerSettings, RetryConfig

@pytest.fixture
def event_loop():
    """テスト用のイベントループを提供するフィクスチャ"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
def session_config() -> PowerShellControllerSettings:
    """テスト用のセッション設定を提供するフィクスチャ"""
    return PowerShellControllerSettings(
        log_level="DEBUG",
        timeout=3.0,  # タイムアウトをさらに短く設定
        retry_config=RetryConfig(
            max_attempts=1,  # リトライなし
            base_delay=0.1,
            max_delay=0.5,
            jitter=0.05
        )
    )

@pytest.fixture
async def session(session_config: PowerShellControllerSettings) -> AsyncGenerator[PowerShellSession, None]:
    """テスト用のPowerShellSessionインスタンスを提供するフィクスチャ"""
    session = PowerShellSession(config=session_config.model_dump())
    try:
        async with session:
            yield session
    finally:
        # 確実にセッションをクリーンアップ
        await session.cleanup() 