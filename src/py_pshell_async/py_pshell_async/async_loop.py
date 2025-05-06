"""
非同期ループ管理

イベントループの管理とタスク実行のためのユーティリティを提供します。
"""
import asyncio
import functools
import threading
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar, Union, overload, cast

from beartype import beartype
from loguru import logger

# 型変数
T = TypeVar('T')
R = TypeVar('R')

class AsyncLoopManager:
    """
    AsyncLoopManagerはイベントループの管理を抽象化するクラスです。
    
    スレッドの管理、イベントループの作成と管理、非同期処理の同期的な実行などの機能を提供します。
    
    Example:
        ```python
        # インスタンス作成
        loop_manager = AsyncLoopManager()
        
        # 非同期関数の実行
        result = loop_manager.run_in_loop(async_function, arg1, arg2)
        
        # クリーンアップ
        loop_manager.close()
        ```
    """
    
    def __init__(self):
        """AsyncLoopManagerを初期化します。"""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._closed = False
        self._lock = threading.RLock()
        self._logger = logger.bind(module="async_loop_manager")
        
    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """管理されているイベントループを返します。"""
        return self._loop
        
    def get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """
        既存のイベントループを取得するか、新しいループを作成して返します。
        
        Returns:
            asyncio.AbstractEventLoop: イベントループ
        
        Raises:
            RuntimeError: ループマネージャーが既に閉じられている場合
        """
        if self._closed:
            raise RuntimeError("AsyncLoopManager is already closed")
            
        with self._lock:
            if self._loop is None or self._loop.is_closed():
                self._create_new_loop()
            return self._loop
            
    def run_in_loop(self, coro_or_func: Union[Callable[..., Coroutine[Any, Any, T]], Coroutine[Any, Any, T]], *args, **kwargs) -> T:
        """
        コルーチンまたはコルーチンを返す関数を現在のイベントループで実行します。
        
        Args:
            coro_or_func: 実行するコルーチンまたはコルーチンを返す関数
            *args: 関数に渡す引数
            **kwargs: 関数に渡すキーワード引数
            
        Returns:
            T: コルーチンの実行結果
            
        Raises:
            RuntimeError: ループマネージャーが既に閉じられている場合
        """
        if self._closed:
            raise RuntimeError("AsyncLoopManager is already closed")
            
        loop = self.get_or_create_loop()
        
        if asyncio.iscoroutine(coro_or_func):
            coroutine = coro_or_func
        else:
            coroutine = coro_or_func(*args, **kwargs)
            
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            return future.result()
        else:
            return loop.run_until_complete(coroutine)
            
    def create_task(self, coro: Coroutine[Any, Any, T], *, name: Optional[str] = None) -> asyncio.Task[T]:
        """
        コルーチンをタスクとして作成し、現在のイベントループに登録します。
        
        Args:
            coro: タスクとして実行するコルーチン
            name: タスクの名前 (オプション)
            
        Returns:
            asyncio.Task: 作成されたタスク
            
        Raises:
            RuntimeError: ループマネージャーが既に閉じられている場合
        """
        if self._closed:
            raise RuntimeError("AsyncLoopManager is already closed")
            
        loop = self.get_or_create_loop()
        
        if sys.version_info >= (3, 8):
            return loop.create_task(coro, name=name)
        else:
            task = loop.create_task(coro)
            if name is not None:
                task.set_name(name)
            return task
    
    def _create_new_loop(self) -> None:
        """新しいイベントループを作成して設定します。"""
        # もし既存のループがあり、閉じていなければ閉じる
        if self._loop is not None and not self._loop.is_closed():
            warnings.warn("Creating a new event loop while the old one is still open", RuntimeWarning)
            try:
                self._loop.stop()
                self._loop.close()
            except Exception as e:
                self._logger.warning(f"Error closing previous event loop: {e}")
                
        # もし既存のスレッドがあり、実行中であれば終了を待つ
        if self._thread is not None and self._thread.is_alive():
            self._logger.debug("Waiting for previous loop thread to finish")
            self._thread.join(timeout=5.0)
                
        # 新しいイベントループを作成
        self._loop = asyncio.new_event_loop()
        
        # 別スレッドでループを実行
        def run_loop(loop: asyncio.AbstractEventLoop) -> None:
            asyncio.set_event_loop(loop)
            try:
                loop.run_forever()
            except Exception as e:
                self._logger.error(f"Error in event loop: {e}")
            finally:
                loop.close()
                self._logger.debug("Event loop thread finished")
                
        self._thread = threading.Thread(target=run_loop, args=(self._loop,), daemon=True)
        self._thread.start()
        self._logger.debug("Started new event loop in background thread")
        
    def close(self) -> None:
        """
        イベントループと関連リソースを閉じます。
        
        このメソッドは、ループマネージャーが不要になった場合に呼び出してください。
        """
        if self._closed:
            return
            
        with self._lock:
            self._closed = True
            
            if self._loop is not None and not self._loop.is_closed():
                # ループ内のすべてのタスクをキャンセル
                for task in asyncio.all_tasks(self._loop):
                    task.cancel()
                    
                # ループを停止
                self._loop.call_soon_threadsafe(self._loop.stop)
                
                # ループが完全に終了するのを待つ
                if self._thread is not None and self._thread.is_alive():
                    self._thread.join(timeout=5.0)
                    
                # ループを閉じる
                if not self._loop.is_closed():
                    self._loop.close()
                    
            # エグゼキューターを閉じる
            self._executor.shutdown(wait=False)
            
            self._logger.debug("AsyncLoopManager closed")
            
    def __del__(self) -> None:
        """オブジェクトが破棄されるときにリソースを解放します。"""
        try:
            self.close()
        except Exception as e:
            pass


# グローバルインスタンス
_global_loop_manager = AsyncLoopManager()

@beartype
def get_event_loop() -> asyncio.AbstractEventLoop:
    """
    現在のイベントループを取得します。
    
    ループがない場合は新しいループを作成します。
    
    Returns:
        asyncio.AbstractEventLoop: イベントループ
    """
    return _global_loop_manager.get_or_create_loop()

@beartype
def run_in_loop(coro_or_func: Union[Callable[..., Coroutine[Any, Any, T]], Coroutine[Any, Any, T]], *args, **kwargs) -> T:
    """
    コルーチンまたはコルーチンを返す関数をグローバルイベントループで実行します。
    
    Args:
        coro_or_func: 実行するコルーチンまたはコルーチンを返す関数
        *args: 関数に渡す引数
        **kwargs: 関数に渡すキーワード引数
        
    Returns:
        T: コルーチンの実行結果
    """
    return _global_loop_manager.run_in_loop(coro_or_func, *args, **kwargs)

@beartype
def create_task(coro: Coroutine[Any, Any, T], *, name: Optional[str] = None) -> asyncio.Task[T]:
    """
    コルーチンをタスクとして作成し、グローバルイベントループに登録します。
    
    Args:
        coro: タスクとして実行するコルーチン
        name: タスクの名前 (オプション)
        
    Returns:
        asyncio.Task: 作成されたタスク
    """
    return _global_loop_manager.create_task(coro, name=name)

@beartype
def run_as_task(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., asyncio.Task[T]]:
    """
    コルーチン関数をタスクとして実行するデコレータです。
    
    Args:
        func: コルーチン関数
        
    Returns:
        Callable: タスクを返すラッパー関数
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> asyncio.Task[T]:
        coro = func(*args, **kwargs)
        return create_task(coro)
    return wrapper 