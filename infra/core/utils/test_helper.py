"""
テスト用のヘルパー機能
"""
import asyncio
from typing import Any, Callable
from .errors import PowerShellTimeoutError, PowerShellExecutionError

class AsyncTestHelper:
    """テスト用の非同期ヘルパークラス"""
    
    @staticmethod
    async def wait_for_condition(
        condition: Callable[[], bool],
        timeout: float = 5.0,
        interval: float = 0.1,
        error_message: str = "Condition not met within timeout"
    ) -> None:
        """
        条件が満たされるまで待機する

        Args:
            condition: 条件を確認するコールバック関数
            timeout: タイムアウト時間（秒）
            interval: チェック間隔（秒）
            error_message: タイムアウト時のエラーメッセージ

        Raises:
            PowerShellTimeoutError: タイムアウト時
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if condition():
                return
                
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise PowerShellTimeoutError(error_message)
                
            await asyncio.sleep(interval)

    @staticmethod
    async def async_retry(
        func: Callable,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        exceptions: tuple = (Exception,)
    ) -> Any:
        """
        非同期関数を再試行する

        Args:
            func: 実行する非同期関数
            max_attempts: 最大試行回数
            delay: 初期待機時間（秒）
            backoff_factor: バックオフ係数
            exceptions: 捕捉する例外タプル

        Returns:
            Any: 関数の実行結果

        Raises:
            PowerShellExecutionError: すべての試行が失敗した場合
        """
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                return await func()
            except exceptions as e:
                last_error = e
                if attempt < max_attempts - 1:
                    wait_time = delay * (backoff_factor ** attempt)
                    await asyncio.sleep(wait_time)
                    
        raise PowerShellExecutionError(
            f"All {max_attempts} attempts failed: {str(last_error)}"
        ) from last_error 