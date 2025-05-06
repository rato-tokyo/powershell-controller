"""
非同期プロセス管理のためのユーティリティ

このモジュールはより効率的で信頼性の高い非同期プロセス管理を提供します。
"""
import asyncio
import time
import signal
import os
import sys
import psutil
from typing import Any, Callable, Optional, TypeVar, Coroutine, Dict, List, Union, Set
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ...core.errors import PowerShellTimeoutError, ProcessError, CommunicationError

T = TypeVar('T')

class ProcessStats:
    """プロセス統計情報クラス"""
    
    def __init__(self, pid: int):
        """
        プロセス統計情報を初期化します。
        
        Args:
            pid: プロセスID
        """
        self.pid = pid
        self.start_time = time.time()
        self.cpu_usage: List[float] = []
        self.memory_usage: List[float] = []
        self.last_update = self.start_time
        
    def update(self, process: psutil.Process) -> None:
        """
        プロセスの統計情報を更新します。
        
        Args:
            process: psutilプロセスオブジェクト
        """
        try:
            self.cpu_usage.append(process.cpu_percent())
            self.memory_usage.append(process.memory_percent())
            self.last_update = time.time()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    def get_avg_cpu(self) -> float:
        """平均CPU使用率を取得します。"""
        return sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0.0
        
    def get_avg_memory(self) -> float:
        """平均メモリ使用率を取得します。"""
        return sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0.0
        
    def get_uptime(self) -> float:
        """プロセスの稼働時間（秒）を取得します。"""
        return time.time() - self.start_time


class AsyncProcessManager:
    """より効率的な非同期プロセス管理クラス"""
    
    def __init__(self, max_workers: int = 4):
        """
        AsyncProcessManagerを初期化します。
        
        Args:
            max_workers: スレッドプールの最大ワーカー数
        """
        self.logger = logger.bind(module="async_process_manager")
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: Dict[str, asyncio.Task] = {}
        self._monitored_processes: Dict[int, ProcessStats] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_monitoring = asyncio.Event()
        
    async def start_monitoring(self, interval: float = 5.0) -> None:
        """
        プロセス監視を開始します。
        
        Args:
            interval: 監視間隔（秒）
        """
        if self._monitoring_task is not None:
            return
            
        async def _monitor():
            while not self._stop_monitoring.is_set():
                try:
                    self._update_process_stats()
                    # 異常プロセスの検出
                    await self._detect_anomalies()
                except Exception as e:
                    self.logger.error(f"プロセス監視中にエラーが発生: {e}")
                finally:
                    try:
                        await asyncio.wait_for(
                            self._stop_monitoring.wait(),
                            timeout=interval
                        )
                    except asyncio.TimeoutError:
                        pass  # 監視継続
        
        self._monitoring_task = asyncio.create_task(_monitor())
        self.logger.info("プロセス監視を開始しました")
        
    def _update_process_stats(self) -> None:
        """各監視対象プロセスの統計情報を更新します。"""
        for pid, stats in list(self._monitored_processes.items()):
            try:
                process = psutil.Process(pid)
                if process.is_running():
                    stats.update(process)
                else:
                    # プロセスが終了している場合は監視対象から削除
                    self.logger.info(f"プロセス {pid} は実行されていないため監視を停止します")
                    del self._monitored_processes[pid]
            except psutil.NoSuchProcess:
                # プロセスが存在しない場合は監視対象から削除
                self.logger.info(f"プロセス {pid} は存在しないため監視を停止します")
                del self._monitored_processes[pid]
            except Exception as e:
                self.logger.warning(f"プロセス {pid} の統計更新中にエラーが発生: {e}")
                
    async def _detect_anomalies(self) -> None:
        """異常プロセスを検出します（高CPU使用率、高メモリ使用率、ゾンビなど）"""
        for pid, stats in list(self._monitored_processes.items()):
            try:
                process = psutil.Process(pid)
                
                # 応答のないプロセスを検出（最後の更新から長時間経過）
                if time.time() - stats.last_update > 30:  # 30秒以上応答なし
                    self.logger.warning(f"プロセス {pid} が応答していない可能性があります")
                
                # 高CPU使用率の検出 (90%以上)
                if stats.get_avg_cpu() > 90:
                    self.logger.warning(f"プロセス {pid} のCPU使用率が異常です: {stats.get_avg_cpu()}%")
                
                # 高メモリ使用率の検出 (80%以上)
                if stats.get_avg_memory() > 80:
                    self.logger.warning(f"プロセス {pid} のメモリ使用率が異常です: {stats.get_avg_memory()}%")
                    
                # プロセスのステータスチェック
                if process.status() == psutil.STATUS_ZOMBIE:
                    self.logger.warning(f"プロセス {pid} はゾンビ状態です")
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                self.logger.error(f"プロセス {pid} の異常検出中にエラーが発生: {e}")
    
    def register_process(self, pid: int) -> None:
        """
        プロセスを監視対象に登録します。
        
        Args:
            pid: 監視対象のプロセスID
        """
        if pid not in self._monitored_processes:
            try:
                # プロセスの存在確認
                process = psutil.Process(pid)
                if process.is_running():
                    self._monitored_processes[pid] = ProcessStats(pid)
                    self.logger.info(f"プロセス {pid} を監視対象に登録しました")
                    
                    # 監視タスクが動いていなければ開始
                    if self._monitoring_task is None:
                        asyncio.create_task(self.start_monitoring())
            except psutil.NoSuchProcess:
                self.logger.warning(f"プロセス {pid} は存在しないため登録できません")
            except Exception as e:
                self.logger.error(f"プロセス {pid} の登録中にエラーが発生: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ProcessError, CommunicationError))
    )
    async def run_in_executor(
        self,
        func: Callable[..., T],
        timeout: float = 10.0,
        task_id: Optional[str] = None,
        **kwargs: Any
    ) -> T:
        """
        関数をExecutorで実行します。タイムアウト付き。
        
        Args:
            func: 実行する関数
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
        
        # ThreadPoolExecutorで関数を実行
        future = self._executor.submit(func, **kwargs)
        self.logger.debug(f"タスク {task_id} を開始しました")
        
        try:
            # asyncioに適合させるため、ループ内でfutureの完了を待機
            loop = asyncio.get_event_loop()
            
            # タイムアウト付きでループを介して待機
            start_time = time.time()
            
            while not future.done():
                if time.time() - start_time > timeout:
                    future.cancel()
                    raise PowerShellTimeoutError(f"タスク {task_id} が {timeout} 秒でタイムアウトしました")
                
                # 短い間隔で確認し続ける
                await asyncio.sleep(0.1)
            
            # 結果の取得
            return future.result()
            
        except PowerShellTimeoutError:
            raise
        except Exception as e:
            self.logger.error(f"タスク {task_id} の実行中にエラーが発生: {e}")
            raise ProcessError(f"タスク {task_id} の実行に失敗しました: {e}")
    
    @asynccontextmanager
    async def create_monitored_task(
        self, 
        coro: Coroutine[Any, Any, T],
        task_id: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        """
        監視されたタスクを作成し、実行します。コンテキストマネージャとして使用します。
        
        Args:
            coro: 実行するコルーチン
            task_id: タスク識別子
            timeout: タイムアウト時間（秒）
            
        Yields:
            asyncio.Task: 作成されたタスク
            
        Example:
            async with process_manager.create_monitored_task(some_coro()) as task:
                # タスクが実行中...
                result = await task
        """
        task_id = task_id or f"task_{id(coro)}"
        task = asyncio.create_task(coro, name=task_id)
        self._tasks[task_id] = task
        
        # タイムアウト処理用タスク
        timeout_task = None
        if timeout is not None:
            async def _timeout_handler():
                await asyncio.sleep(timeout)
                if not task.done():
                    task.cancel()
                    self.logger.warning(f"タスク {task_id} が {timeout} 秒でタイムアウトしました")
            
            timeout_task = asyncio.create_task(_timeout_handler())
        
        try:
            self.logger.debug(f"タスク {task_id} の監視を開始しました")
            yield task
        finally:
            if task_id in self._tasks:
                del self._tasks[task_id]
            
            # タイムアウトハンドラがあれば停止
            if timeout_task is not None and not timeout_task.done():
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass
    
    async def terminate_process(self, pid: int, force: bool = False, timeout: float = 5.0) -> bool:
        """
        プロセスを終了します。
        
        Args:
            pid: 終了するプロセスのID
            force: 強制終了するかどうか
            timeout: 終了待機タイムアウト（秒）
            
        Returns:
            bool: 終了に成功した場合はTrue
        """
        try:
            process = psutil.Process(pid)
            
            if not process.is_running():
                self.logger.info(f"プロセス {pid} は既に終了しています")
                return True
            
            # プロセスの子プロセスを取得
            try:
                children = process.children(recursive=True)
            except psutil.Error:
                children = []
            
            # まずSIGTERMでプロセスを終了させる
            self.logger.info(f"プロセス {pid} に終了シグナルを送信中...")
            process.terminate()
            
            try:
                # 指定時間内にプロセスが終了するのを待機
                gone, alive = psutil.wait_procs([process], timeout=timeout)
                if process in alive:
                    # タイムアウト後も生きている場合
                    if force:
                        self.logger.warning(f"プロセス {pid} を強制終了します")
                        process.kill()
                    else:
                        self.logger.warning(f"プロセス {pid} はまだ実行中です")
                        return False
            except psutil.Error:
                # プロセスが既に存在しない場合
                pass
            
            # 子プロセスも終了
            for child in children:
                try:
                    if child.is_running():
                        child.terminate()
                        try:
                            child.wait(timeout=timeout/2)
                        except psutil.TimeoutExpired:
                            if force:
                                child.kill()
                except psutil.Error:
                    pass
            
            # 監視対象から削除
            if pid in self._monitored_processes:
                del self._monitored_processes[pid]
                
            return True
            
        except psutil.NoSuchProcess:
            self.logger.info(f"プロセス {pid} は存在しません")
            # 監視対象から削除
            if pid in self._monitored_processes:
                del self._monitored_processes[pid]
            return True
        except Exception as e:
            self.logger.error(f"プロセス {pid} の終了中にエラーが発生: {e}")
            return False
    
    async def cleanup(self) -> None:
        """
        実行中のすべてのタスクとプロセスをクリーンアップします。
        """
        # 監視タスクの停止
        if self._monitoring_task is not None:
            self._stop_monitoring.set()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        # 監視対象プロセスの終了
        pids_to_terminate = list(self._monitored_processes.keys())
        for pid in pids_to_terminate:
            await self.terminate_process(pid, force=True)
        
        # タスクのキャンセル
        self.logger.debug(f"{len(self._tasks)} 個のタスクをクリーンアップしています")
        for task_id, task in list(self._tasks.items()):
            self.logger.debug(f"タスク {task_id} をキャンセルしています")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.warning(f"タスク {task_id} のキャンセル中にエラーが発生: {e}")
            finally:
                if task_id in self._tasks:
                    del self._tasks[task_id]
        
        # エグゼキュータのシャットダウン
        self._executor.shutdown(wait=False)
        self.logger.debug("クリーンアップが完了しました") 