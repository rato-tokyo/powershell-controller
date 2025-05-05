"""
非同期プロセス管理のためのユーティリティ
"""
import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar, Coroutine, Dict
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ...core.errors import PowerShellTimeoutError, ProcessError

T = TypeVar('T')

class AsyncProcessManager:
    """非同期プロセス管理クラス"""
    
    def __init__(self, max_workers: int = 4):
        """
        AsyncProcessManagerを初期化します。
        
        Args:
            max_workers: スレッドプールの最大ワーカー数
        """
        self.logger = logger.bind(module="async_process_manager")
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, asyncio.Task] = {}
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(ProcessError)
    )
    async def run_in_executor(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        timeout: float = 10.0,
        task_id: Optional[str] = None,
        **kwargs: Any
    ) -> T:
        """
        非同期関数をExecutorで実行します。タイムアウト付き。
        tenacityを使用した自動リトライ機能を実装しています。
        
        Args:
            func: 実行する非同期関数
            timeout: タイムアウト時間（秒）
            task_id: タスク識別子（オプション）
            **kwargs: 関数に渡す引数
            
        Returns:
            関数の実行結果
            
        Raises:
            PowerShellTimeoutError: タイムアウト発生時
            ProcessError: 実行エラー発生時
        """
        task_id = task_id or f"task_{id(func)}"
        
        async def wrapped_func():
            try:
                self.logger.debug(f"Starting task {task_id}")
                return await func(**kwargs)
            except Exception as e:
                self.logger.error(f"Error in task {task_id}: {e}")
                raise ProcessError(f"Task execution failed: {e}") from e
            finally:
                self.logger.debug(f"Completed task {task_id}")
        
        task = asyncio.create_task(wrapped_func())
        self._tasks[task_id] = task
        
        try:
            return await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            raise PowerShellTimeoutError(f"Task {task_id} timed out after {timeout} seconds")
        except Exception as e:
            if not isinstance(e, PowerShellTimeoutError):
                raise ProcessError(f"Task {task_id} failed: {e}") from e
            raise
        finally:
            if task_id in self._tasks:
                del self._tasks[task_id]
    
    async def cleanup(self):
        """
        実行中のすべてのタスクをキャンセルします。
        """
        self.logger.debug(f"Cleaning up {len(self._tasks)} tasks")
        for task_id, task in list(self._tasks.items()):
            self.logger.debug(f"Cancelling task {task_id}")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.warning(f"Error during task {task_id} cancellation: {e}")
            finally:
                if task_id in self._tasks:
                    del self._tasks[task_id]
        
        self._executor.shutdown(wait=False)
        self.logger.debug("Cleanup completed") 