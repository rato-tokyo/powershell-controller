"""
プロセス管理のユーティリティ
"""
import asyncio
import logging
from typing import Any, Callable, Optional, Dict
from concurrent.futures import ThreadPoolExecutor
from .errors import PowerShellTimeoutError, PowerShellExecutionError

logger = logging.getLogger(__name__)

class AsyncProcessManager:
    """非同期プロセス管理クラス"""
    
    def __init__(self, max_workers: int = 4):
        """
        Args:
            max_workers (int): 同時実行可能なワーカー数
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, asyncio.Task] = {}
    
    async def run_in_executor(
        self,
        func: Callable,
        *args: Any,
        timeout: Optional[float] = None,
        task_id: Optional[str] = None,
        **kwargs: Any
    ) -> Any:
        """
        関数を非同期実行する

        Args:
            func: 実行する関数
            *args: 関数の位置引数
            timeout: タイムアウト時間（秒）
            task_id: タスクID（省略可）
            **kwargs: 関数のキーワード引数

        Returns:
            Any: 関数の実行結果

        Raises:
            PowerShellTimeoutError: タイムアウト時
            PowerShellExecutionError: 実行エラー時
        """
        task_id = task_id or str(id(func))
        
        try:
            if timeout is not None:
                return await asyncio.wait_for(
                    self._execute(func, *args, **kwargs),
                    timeout=timeout
                )
            return await self._execute(func, *args, **kwargs)
            
        except asyncio.TimeoutError:
            raise PowerShellTimeoutError(
                f"Task {task_id} timed out after {timeout} seconds"
            )
        except Exception as e:
            raise PowerShellExecutionError(
                f"Task {task_id} failed: {str(e)}"
            ) from e
        finally:
            if task_id in self._tasks:
                del self._tasks[task_id]

    async def _execute(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        executorで関数を実行する内部メソッド
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            func,
            *args,
            **{k: v for k, v in kwargs.items() if v is not None}
        ) 