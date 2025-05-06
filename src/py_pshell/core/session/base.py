"""
基本的なセッション管理のための抽象基底クラス
"""
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, IO, List, Tuple
import asyncio
import subprocess
import sys
import json
import time
import threading
import queue
import os
import psutil
import logging
from loguru import logger
from ...infra.async_utils.process import AsyncProcessManager
from ...infra.async_utils.test_helper import AsyncTestHelper
from ...infra.ipc.protocol import IPCMessage, IPCProtocol, MessageType
from ..errors import (
    PowerShellError,
    PowerShellTimeoutError,
    PowerShellExecutionError,
    ProcessError,
    CommunicationError
)

class BaseSession(ABC):
    """セッション管理の基底クラス"""
    
    def __init__(self, timeout: float = 30.0):
        """
        セッションを初期化します。
        
        Args:
            timeout: タイムアウト時間（秒）
        """
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.logger = logger.bind(module="base_session")
        self._stop_event = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._cleanup_lock = asyncio.Lock()
        self._is_cleaning_up = False
        
    @abstractmethod
    async def __aenter__(self) -> 'BaseSession':
        """セッションを開始します。"""
        pass
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """セッションを終了します。"""
        await self.cleanup()
        
    @abstractmethod
    async def execute(self, command: str) -> Any:
        """
        コマンドを実行します。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            コマンドの実行結果
        """
        pass
        
    async def cleanup(self):
        """
        セッションのリソースをクリーンアップします。
        このメソッドは複数回呼び出されても安全です。
        """
        async with self._cleanup_lock:
            if self._is_cleaning_up:
                return
                
            self._is_cleaning_up = True
            try:
                self._stop_event.set()
                await self._cleanup_resources()
            finally:
                self._is_cleaning_up = False
                
    @abstractmethod
    async def _cleanup_resources(self):
        """
        具体的なリソースのクリーンアップを実装します。
        このメソッドは派生クラスで実装する必要があります。
        """
        pass
        
    async def restart(self):
        """
        セッションを再起動します。
        """
        self.logger.info("Restarting session...")
        
        # 既存のリソースをクリーンアップ
        await self.cleanup()
        
        # 状態をリセット
        self._stop_event.clear()
        self._is_cleaning_up = False
        self._output_queue = asyncio.Queue()
        self._error_queue = asyncio.Queue()
        
        # 新しいプロセスを起動
        try:
            await self.__aenter__()
            self.logger.info("Session restarted successfully")
        except Exception as e:
            error_msg = f"Failed to restart session: {e}"
            self.logger.error(error_msg)
            raise ProcessError(error_msg)
        
    def _start_io_tasks(self):
        """
        入出力タスクを開始します。
        """
        if not hasattr(self, '_output_queue') or not hasattr(self, '_error_queue'):
            raise RuntimeError("IO queues not initialized")
            
        if not hasattr(self, 'process') or not self.process:
            raise RuntimeError("Process not initialized")
            
        if not self.process.stdout or not self.process.stderr:
            raise RuntimeError("Process streams not initialized")
            
        asyncio.create_task(
            self._read_pipe(
                self.process.stdout,
                self._output_queue,
                "stdout"
            )
        )
        asyncio.create_task(
            self._read_pipe(
                self.process.stderr,
                self._error_queue,
                "stderr"
            )
        )
        
    async def _read_pipe(self, pipe: asyncio.StreamReader, output_queue: asyncio.Queue, name: str) -> None:
        """
        パイプからデータを読み取ります。
        
        Args:
            pipe: 読み取るパイプ
            output_queue: 出力を格納するキュー
            name: パイプの名前（ログ用）
        """
        try:
            while not self._stop_event.is_set():
                try:
                    line = await pipe.readline()
                    if not line:  # EOFに達した場合
                        self.logger.debug(f"{name} reached EOF")
                        break
                        
                    try:
                        decoded_line = line.decode().strip()
                        if decoded_line:
                            # IPCプロトコルを使用してメッセージを解析
                            message = IPCProtocol.parse_output(decoded_line)
                            if message:
                                await output_queue.put(message)
                            else:
                                await output_queue.put(decoded_line)
                            self.logger.debug(f"{name} received: {decoded_line}")
                    except UnicodeDecodeError as e:
                        self.logger.error(f"Failed to decode {name} output: {e}")
                        continue
                        
                except asyncio.CancelledError:
                    self.logger.info(f"{name} reader cancelled")
                    break
                except Exception as e:
                    error_msg = str(e)
                    self.logger.error(f"Error reading from {name}: {error_msg}")
                    if not self._stop_event.is_set():
                        error_message = IPCProtocol.create_error_message(
                            CommunicationError(
                                f"Error reading from {name}",
                                direction="receive",
                                data=error_msg
                            )
                        )
                        await output_queue.put(error_message)
                    break
                    
        finally:
            self.logger.debug(f"{name} reader stopped")
            await output_queue.put(None)  # 終了を通知
            
    async def _read_queues(self, timeout: float = None) -> Tuple[List[str], List[str]]:
        """
        出力キューとエラーキューから読み取りを行う
        
        Args:
            timeout: タイムアウト時間（秒）。Noneの場合はデフォルトのタイムアウトを使用
            
        Returns:
            (出力リスト, エラーリスト)のタプル
        """
        if timeout is None:
            timeout = self.timeout
            
        outputs = []
        errors = []
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                break
                
            try:
                output = await asyncio.wait_for(
                    self._output_queue.get(),
                    timeout=0.1
                )
                if output is None:
                    break
                if isinstance(output, IPCMessage):
                    if output.type == MessageType.ERROR:
                        errors.append(output.content)
                    else:
                        outputs.append(output.content)
                else:
                    outputs.append(output)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error reading from output queue: {e}")
                break
                
            try:
                error = await asyncio.wait_for(
                    self._error_queue.get(),
                    timeout=0.1
                )
                if error is None:
                    break
                if isinstance(error, IPCMessage):
                    errors.append(error.content)
                else:
                    errors.append(error)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error reading from error queue: {e}")
                break
                
        return outputs, errors

class BasePowerShellSession(BaseSession):
    """PowerShellセッションの基本クラス"""
    
    def __init__(self, timeout: float = 30.0):
        """
        PowerShellセッションを初期化します。
        
        Args:
            timeout: タイムアウト時間（秒）
        """
        super().__init__(timeout)
        self.process: Optional[asyncio.subprocess.Process] = None
        self._ps_process: Optional[psutil.Process] = None
        self._output_queue: asyncio.Queue = asyncio.Queue()
        self._error_queue: asyncio.Queue = asyncio.Queue()
        self._process_manager = AsyncProcessManager()
        
    async def __aenter__(self) -> 'BasePowerShellSession':
        """セッションを開始します。"""
        await self._start_process()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """セッションを終了します。"""
        await self._stop_process()
        
    async def _start_process(self):
        """PowerShellプロセスを開始します。"""
        if self.process:
            return
        
        try:
            self.process = await asyncio.create_loop_subprocess_exec(
                sys.executable,
                "-m",
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Start-Process -PassThru -NoNewWindow -Wait -ErrorAction Stop -InputObject $null"
            )
            self._ps_process = psutil.Process(self.process.pid)
            self.logger.info("PowerShell process started")
        except Exception as e:
            error_msg = f"Failed to start PowerShell process: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
    async def _stop_process(self):
        """PowerShellプロセスを停止します。"""
        if not self.process:
            return
        
        try:
            self.process.terminate()
            await self.process.wait()
            self.process = None
            self._ps_process = None
            self.logger.info("PowerShell process stopped")
        except Exception as e:
            error_msg = f"Failed to stop PowerShell process: {e}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
    async def _execute_raw(self, script: str) -> str:
        """
        PowerShellスクリプトを実行し、結果を返す
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            実行結果
        """
        if not self.process or not self.process.stdin:
            raise RuntimeError("PowerShell process is not initialized")
            
        try:
            # スクリプトを送信
            await self.process.stdin.write((script + "\n").encode())
            await self.process.stdin.drain()
            
            # 結果を読み取り
            outputs, errors = await self._read_queues(timeout=self.timeout)
            
            # エラーチェック
            if errors:
                error_msg = "ERROR: " + "; ".join(errors)
                self.logger.error(f"Error executing script: {error_msg}")
                raise RuntimeError(error_msg)
                
            # 結果を返す
            if outputs:
                return outputs[-1]  # 最後の出力を返す
            return ""
            
        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            self.logger.error(f"Error executing script: {error_msg}")
            raise RuntimeError(error_msg)
            
    async def execute(self, command: str) -> Any:
        """
        PowerShellコマンドを実行し、結果を返す
        
        Args:
            command: 実行するコマンド
            
        Returns:
            実行結果
        """
        script = f"Execute-Command -Command '{command}'"
        result = await self._execute_raw(script)
        
        try:
            # JSON形式の場合はパース
            if result.startswith("JSON_START") and result.endswith("JSON_END"):
                json_str = result[len("JSON_START"):].strip()[:-len("JSON_END")].strip()
                return json.loads(json_str)
            return result
        except Exception as e:
            self.logger.error(f"Error parsing command output: {e}")
            return result
            
    def execute_sync(self, command: str) -> Any:
        """
        同期的にPowerShellコマンドを実行
        
        Args:
            command: 実行するコマンド
            
        Returns:
            実行結果
        """
        async def _run():
            return await self.execute(command)
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close() 