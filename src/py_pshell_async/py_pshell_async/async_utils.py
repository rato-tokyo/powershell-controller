"""
非同期ユーティリティ

非同期処理のためのユーティリティ関数とクラスを提供します。
"""
import asyncio
import contextlib
import functools
from typing import Any, Awaitable, Callable, Dict, Generic, List, Optional, Set, TypeVar, Union, cast
import time
import warnings
from loguru import logger

T = TypeVar('T')
R = TypeVar('R')

class TaskManager:
    """
    タスク管理クラス
    
    非同期タスクを作成・追跡・キャンセルするための機能を提供します。
    """
    
    def __init__(self):
        """TaskManagerを初期化します。"""
        self._tasks: Set[asyncio.Task] = set()
        self._logger = logger.bind(module="task_manager")
        
    def create_task(self, coro: Awaitable[T], *, name: Optional[str] = None) -> asyncio.Task[T]:
        """
        コルーチンからタスクを作成し、管理対象に追加します。
        
        Args:
            coro: タスクとして実行するコルーチン
            name: タスクの名前 (Python 3.8以上)
            
        Returns:
            asyncio.Task: 作成されたタスク
        """
        if hasattr(asyncio, "create_task") and name is not None:
            task = asyncio.create_task(coro, name=name)
        else:
            task = asyncio.create_task(coro)
            if name is not None and hasattr(task, "set_name"):
                task.set_name(name)
                
        self._tasks.add(task)
        task.add_done_callback(self._task_done_callback)
        return task
        
    def _task_done_callback(self, task: asyncio.Task) -> None:
        """タスクが完了したときに呼び出されるコールバック。"""
        if task in self._tasks:
            self._tasks.remove(task)
            
        # キャンセルされていないエラーがあればログに記録
        if not task.cancelled():
            exc = task.exception()
            if exc:
                name = task.get_name() if hasattr(task, "get_name") else "unknown"
                self._logger.error(f"Task '{name}' raised an exception: {exc}")
                
    async def cancel_all(self, wait: bool = True) -> None:
        """
        すべてのタスクをキャンセルします。
        
        Args:
            wait: タスクの完了を待つかどうか
        """
        # タスクのコピーを作成（反復処理中にセットが変更される可能性があるため）
        tasks = list(self._tasks)
        
        # すべてのタスクをキャンセル
        for task in tasks:
            if not task.done():
                task.cancel()
                
        if wait and tasks:
            # すべてのタスクが完了するのを待つ
            await asyncio.gather(*tasks, return_exceptions=True)
            
        # タスクセットをクリア
        self._tasks.clear()
        
    def get_all_tasks(self) -> List[asyncio.Task]:
        """
        管理されているすべてのタスクのリストを返します。
        
        Returns:
            List[asyncio.Task]: タスクのリスト
        """
        return list(self._tasks)
        
    def get_active_tasks(self) -> List[asyncio.Task]:
        """
        アクティブなタスク（完了していないタスク）のリストを返します。
        
        Returns:
            List[asyncio.Task]: アクティブなタスクのリスト
        """
        return [task for task in self._tasks if not task.done()]
        
    def get_task_count(self) -> int:
        """
        管理されているタスクの総数を返します。
        
        Returns:
            int: タスク数
        """
        return len(self._tasks)
        
    def get_active_task_count(self) -> int:
        """
        アクティブなタスクの数を返します。
        
        Returns:
            int: アクティブなタスク数
        """
        return len(self.get_active_tasks())
        
    def __len__(self) -> int:
        """
        管理されているタスクの総数を返します。
        
        Returns:
            int: タスク数
        """
        return len(self._tasks)
        
    async def wait_for_all(self) -> None:
        """すべてのタスクが完了するまで待機します。"""
        if not self._tasks:
            return
            
        # タスクのコピーを作成
        tasks = list(self._tasks)
        
        # すべてのタスクが完了するのを待つ
        await asyncio.gather(*tasks, return_exceptions=True)


class Semaphore:
    """
    Semaphoreは並行実行数を制限するためのクラスです。
    
    組み込みの asyncio.Semaphore と同様ですが、使用中のセマフォの数を
    追跡するなどの追加機能があります。
    """
    
    def __init__(self, value: int = 1):
        """
        Semaphoreを初期化します。
        
        Args:
            value: 初期値（最大同時実行数）
        """
        if value < 1:
            raise ValueError("Semaphore initial value must be >= 1")
        self._value = value
        self._semaphore = asyncio.Semaphore(value)
        self._active = 0
        
    @property
    def active(self) -> int:
        """現在アクティブなタスクの数を返します。"""
        return self._active
        
    @property
    def value(self) -> int:
        """セマフォの最大値を返します。"""
        return self._value
        
    @property
    def available(self) -> int:
        """利用可能なスロットの数を返します。"""
        return self._value - self._active
        
    async def acquire(self) -> bool:
        """
        セマフォを獲得します。
        
        Returns:
            bool: 獲得に成功した場合はTrue
        """
        result = await self._semaphore.acquire()
        self._active += 1
        return result
        
    def release(self) -> None:
        """セマフォを解放します。"""
        self._semaphore.release()
        self._active -= 1
        
    @contextlib.asynccontextmanager
    async def acquire_context(self):
        """
        セマフォをコンテキストマネージャとして使用するためのラッパー。
        
        Example:
            ```python
            async with semaphore.acquire_context():
                # セマフォを保持している間の処理
                await some_async_function()
            # ここでセマフォは自動的に解放される
            ```
        """
        await self.acquire()
        try:
            yield
        finally:
            self.release()


async def gather_with_concurrency(n: int, *coros: Awaitable[T]) -> List[T]:
    """
    指定された同時実行数で複数のコルーチンを実行します。
    
    Args:
        n: 最大同時実行数
        *coros: 実行するコルーチン
        
    Returns:
        List[T]: 各コルーチンの結果のリスト
    """
    semaphore = Semaphore(n)
    
    async def _wrapped_coro(coro: Awaitable[T]) -> T:
        async with semaphore.acquire_context():
            return await coro
            
    return await asyncio.gather(*(_wrapped_coro(c) for c in coros))


async def gather_limit(limit: int, *tasks: Awaitable[T], return_exceptions: bool = False) -> List[T]:
    """
    指定された最大同時実行数でタスクを実行します。
    
    asyncio.gatherと似ていますが、同時実行数を制限できます。
    
    Args:
        limit: 最大同時実行数
        *tasks: 実行するタスク
        return_exceptions: Trueの場合、例外をキャッチして結果として返します
        
    Returns:
        List[T]: タスクの結果のリスト
    """
    if limit <= 0:
        raise ValueError("Concurrency limit must be positive")
        
    if not tasks:
        return []
        
    queue = asyncio.Queue()
    results = [None] * len(tasks)
    exceptions = []
    
    # すべてのタスクをキューに入れる
    for i, task in enumerate(tasks):
        await queue.put((i, task))
        
    # ワーカータスク
    async def worker():
        while not queue.empty():
            try:
                idx, task = await queue.get()
                try:
                    result = await task
                    results[idx] = result
                except Exception as e:
                    if return_exceptions:
                        results[idx] = e
                    else:
                        exceptions.append(e)
                finally:
                    queue.task_done()
            except asyncio.CancelledError:
                break
                
    # ワーカーを起動
    workers = [asyncio.create_task(worker()) for _ in range(min(limit, len(tasks)))]
    
    # すべてのタスクが完了するのを待つ
    await queue.join()
    
    # ワーカーをキャンセル
    for w in workers:
        w.cancel()
        
    # ワーカーが完了するのを待つ
    await asyncio.gather(*workers, return_exceptions=True)
    
    # 例外が発生していたら最初の例外を再発生
    if exceptions and not return_exceptions:
        raise exceptions[0]
        
    return results


async def complete_or_cancel(coro: Awaitable[T], timeout: float) -> Optional[T]:
    """
    指定されたタイムアウト内にコルーチンが完了しない場合、キャンセルします。
    
    Args:
        coro: 実行するコルーチン
        timeout: タイムアウト時間（秒）
        
    Returns:
        Optional[T]: タイムアウト前に完了した場合はその結果、そうでなければNone
    """
    task = asyncio.create_task(coro)
    
    try:
        return await asyncio.wait_for(task, timeout)
    except asyncio.TimeoutError:
        # タイムアウトした場合、タスクをキャンセル
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return None


@contextlib.asynccontextmanager
async def timeout_handler(seconds: float, message: str = "Operation timed out"):
    """
    指定された時間内にブロックが完了しない場合、例外を発生させるコンテキストマネージャ。
    
    Args:
        seconds: タイムアウト時間（秒）
        message: タイムアウト時のエラーメッセージ
        
    Raises:
        asyncio.TimeoutError: タイムアウトした場合
        
    Example:
        ```python
        async with timeout_handler(5.0, "Database query timed out"):
            await db.execute_query("SELECT * FROM large_table")
        ```
    """
    try:
        yield await asyncio.wait_for(asyncio.sleep(seconds, result=None), seconds)
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(message) 