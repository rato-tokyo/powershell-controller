"""
非同期テストのためのヘルパークラス
"""
from typing import Any, Callable, Coroutine, Optional, Type, Tuple, Union
import asyncio
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ...core.errors import PowerShellExecutionError

class AsyncTestHelper:
    """非同期テストのためのヘルパークラス"""
    
    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, min=0.1, max=1.0),
        retry=retry_if_exception_type(Exception)
    )
    async def async_retry(
        func: Callable[..., Coroutine[Any, Any, Any]],
        max_attempts: int = 3,
        delay: float = 0.1,
        backoff_factor: float = 2.0,
        exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
    ) -> Any:
        """
        非同期関数をリトライ付きで実行します。
        tenacityパッケージを使用した自動リトライ機能を実装しています。
        
        Args:
            func: 実行する非同期関数
            max_attempts: 最大試行回数
            delay: 初期待機時間（秒）
            backoff_factor: バックオフ係数
            exceptions: キャッチする例外のタイプ
            
        Returns:
            関数の実行結果
            
        Raises:
            PowerShellExecutionError: すべての試行が失敗した場合
        """
        log = logger.bind(module="async_test_helper")
        last_error = None
        current_delay = delay
        
        for attempt in range(max_attempts):
            try:
                return await func()
            except exceptions as e:
                last_error = e
                if attempt < max_attempts - 1:
                    log.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {current_delay:.1f} seconds..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
                else:
                    log.error(f"All {max_attempts} attempts failed. Last error: {e}")
                    
        raise PowerShellExecutionError(
            f"Failed after {max_attempts} attempts",
            str(last_error)
        ) 