"""
非同期プロセス管理のためのユーティリティ
"""
import asyncio
import logging
from typing import Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..core.errors import PowerShellTimeoutError, ProcessError

class AsyncProcessManager:
    """非同期プロセス管理クラス"""
    
    def __init__(self) -> None:
        """AsyncProcessManagerを初期化します。"""
        self.logger = logger.bind(module="legacy_process_manager")
        self._executor = ThreadPoolExecutor(max_workers=4)
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(ProcessError)
    )
    async def run_in_executor(
        self,
        func: Callable[..., Any],
        timeout: float = 10.0,
        task_id: Optional[str] = None,
        **kwargs: Any
    ) -> Any:
        """
        関数を別スレッドで実行します。
        
        Args:
            func: 実行する関数
            timeout: タイムアウト時間（秒）
            task_id: タスクの識別子（ログ用）
            **kwargs: 関数に渡す引数
            
        Returns:
            関数の実行結果
            
        Raises:
            PowerShellTimeoutError: タイムアウト時
            ProcessError: 処理エラー時
            Exception: その他のエラー
        """
        task_name = task_id or func.__name__
        self.logger.debug(f"Starting task {task_name}")
        
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(self._executor, func, **kwargs),
                timeout=timeout
            )
            self.logger.debug(f"Task {task_name} completed successfully")
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"Task {task_name} timed out after {timeout} seconds")
            raise PowerShellTimeoutError(f"Task {task_name} timed out")
            
        except Exception as e:
            self.logger.error(f"Task {task_name} failed: {str(e)}")
            raise ProcessError(f"Task execution failed: {e}") from e 