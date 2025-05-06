"""
PowerShellセッションを管理するためのコンテキストマネージャ
"""
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
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
import platform

from ..errors import (
    PowerShellError,
    PowerShellTimeoutError,
    PowerShellExecutionError,
    ProcessError,
    CommunicationError,
    ConfigurationError,
    as_async_result
)
from ...infra.async_utils.process import AsyncProcessManager
from ...infra.async_utils.test_helper import AsyncTestHelper
from ...infra.ipc.protocol import IPCMessage, IPCProtocol, MessageType
from ...utils.config import PowerShellControllerSettings
from .base import BaseSession

class PowerShellSession(BaseSession):
    """PowerShellセッションを管理するコンテキストマネージャ"""
    
    def __init__(self, settings: Optional[PowerShellControllerSettings] = None, timeout: Optional[float] = None):
        """
        PowerShellセッションを初期化します。
        
        Args:
            settings: PowerShellの設定。Noneの場合はデフォルト設定を使用。
            timeout: タイムアウト時間（秒）。Noneの場合は設定から取得。
        """
        # 設定を初期化
        self.settings = settings or PowerShellControllerSettings()
        
        # タイムアウト値を設定（引数が優先）
        actual_timeout = timeout or self.settings.timeouts.default
        super().__init__(actual_timeout)
        
        # セッション状態の初期化
        self.process: Optional[asyncio.subprocess.Process] = None
        self._ps_process: Optional[psutil.Process] = None
        self._output_queue: asyncio.Queue = asyncio.Queue()
        self._error_queue: asyncio.Queue = asyncio.Queue()
        self._process_manager = AsyncProcessManager()
        
        # タイムアウト設定
        self._startup_timeout = self.settings.timeouts.startup
        self._execution_timeout = self.settings.timeouts.execution
        self._read_timeout = self.settings.timeouts.read
        self._shutdown_timeout = self.settings.timeouts.shutdown
        self._cleanup_timeout = self.settings.timeouts.cleanup
        
        # 状態追跡
        self._last_command: str = ""
        self._platform = platform.system().lower()
        self.logger = logger.bind(module="powershell_session")
        
    async def __aenter__(self) -> 'PowerShellSession':
        """セッションを開始します。"""
        try:
            # イベントループを取得
            self._loop = asyncio.get_event_loop()
            
            # PowerShellプロセスを起動
            try:
                # プロセスを作成
                self.logger.debug("PowerShellセッションを開始しています")
                await asyncio.wait_for(
                    self._start_powershell_process(),
                    timeout=self._startup_timeout
                )
                self.logger.info(f"PowerShell process started with PID {self.process.pid}")
                
            except asyncio.TimeoutError:
                raise PowerShellTimeoutError(f"PowerShellセッションの初期化がタイムアウトしました（{self._startup_timeout}秒）")
            
            # 出力とエラーの読み取りタスクを開始
            self._start_io_tasks()
            
            # 初期化完了を待機
            try:
                await asyncio.wait_for(
                    self._wait_for_ready(),
                    timeout=self._startup_timeout
                )
                self.logger.info("PowerShell session initialized successfully")
            except asyncio.TimeoutError:
                raise PowerShellTimeoutError(f"PowerShell session initialization timed out after {self._startup_timeout} seconds")
            except Exception as e:
                raise ProcessError(f"Failed to initialize PowerShell session: {e}")
            
            return self
            
        except Exception as e:
            self.logger.error(f"Error during PowerShell session initialization: {e}")
            await self._cleanup_resources()
            raise PowerShellError.from_exception(e, "PowerShellセッションの初期化に失敗しました")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        retry=retry_if_exception_type(ProcessError)
    )
    async def _start_powershell_process(self) -> None:
        """PowerShellプロセスを起動します。"""
        try:
            # 起動情報の設定
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            # PowerShellのパスを取得
            powershell_path = self.settings.get_ps_path()
            
            # 環境変数を設定
            env = self.settings.get_all_env_vars()
            
            # 引数を取得
            args = self.settings.get_all_args()
            
            # 初期化コマンド
            init_command = self.settings.powershell.init_command
            
            # プロセス起動
            self.logger.debug(f"Starting PowerShell process: {powershell_path}")
            self.process = await asyncio.create_subprocess_exec(
                powershell_path,
                *args,
                "-Command", init_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                startupinfo=startupinfo,
                env=env
            )
            
            if not self.process or not self.process.pid:
                raise ProcessError("Failed to start PowerShell process")
            
            # プロセスの存在確認
            self._verify_process_running()
        
        except Exception as e:
            self.logger.error(f"プロセス起動エラー: {e}")
            raise ProcessError(f"PowerShellプロセスの起動に失敗しました: {e}")
    
    def _verify_process_running(self) -> None:
        """プロセスが実際に動作しているか確認します"""
        if not self.process or not self.process.pid:
            raise ProcessError("プロセスが正常に起動していません")
        
        try:
            # psutilプロセスを取得
            self._ps_process = psutil.Process(self.process.pid)
            if not self._ps_process.is_running():
                raise ProcessError("PowerShellプロセスの実行に失敗しました")
                
            self.logger.debug(f"PowerShellプロセスの起動を確認: PID {self.process.pid}")
            
        except psutil.NoSuchProcess:
            raise ProcessError(f"プロセス(PID {self.process.pid})が見つかりません")
        except psutil.AccessDenied:
            self.logger.warning(f"プロセス(PID {self.process.pid})へのアクセスが拒否されましたが、実行は継続します")
        except Exception as e:
            raise ProcessError(f"プロセスの検証に失敗しました: {e}")
            
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """セッションを終了します。"""
        self._stop_event.set()
        
        if self.process:
            try:
                # EXIT コマンドを送信してきれいに終了させる
                try:
                    if self.process.stdin and not self.process.stdin.is_closing():
                        self.logger.debug("Sending EXIT command to PowerShell process")
                        self.process.stdin.write(b"EXIT\n")
                        await self.process.stdin.drain()
                except Exception as e:
                    self.logger.warning(f"Failed to send EXIT command: {e}")
                
                # 一定時間待機してからプロセスを終了
                try:
                    await asyncio.wait_for(
                        self._process_manager.run_in_executor(
                            self._wait_for_process_exit,
                            timeout=self._shutdown_timeout,
                            task_id="ps_process_termination"
                        ),
                        timeout=self._shutdown_timeout
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("Process termination timed out, forcing termination")
                    await self._terminate_process()
            except Exception as e:
                self.logger.error(f"Error during process termination: {e}")
            finally:
                # クリーンアップ処理を実行
                await self._cleanup_resources()
    
    async def _terminate_process(self) -> None:
        """プロセスを強制終了します"""
        if not self.process:
            return
            
        try:
            # terminateを試す
            self.process.terminate()
            
            # 短い時間待つ
            try:
                await asyncio.wait_for(
                    self._wait_for_process_exit(),
                    timeout=2.0
                )
                return  # 成功して終了
            except asyncio.TimeoutError:
                self.logger.warning("Process still running after terminate, killing it")
            
            # killを試す
            self.process.kill()
            
            # psutilでも試みる
            if self._ps_process and self._ps_process.is_running():
                try:
                    self._ps_process.kill()
                except Exception as e:
                    self.logger.error(f"psutilでのプロセス終了に失敗: {e}")
                    
        except Exception as e:
            self.logger.error(f"プロセス終了エラー: {e}")
    
    async def _wait_for_process_exit(self) -> None:
        """プロセスの終了を待機します。"""
        if self.process:
            await self.process.wait()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((CommunicationError, ProcessError))
    )
    async def _read_queues(self, timeout: float = None) -> Tuple[List[str], List[str]]:
        """
        出力キューとエラーキューから読み取りを行う
        
        Args:
            timeout: タイムアウト時間。Noneの場合はデフォルト値を使用。
            
        Returns:
            (標準出力のリスト, 標準エラー出力のリスト)
        """
        timeout = timeout or self._read_timeout
        
        # クローズされたキューがあれば例外
        if getattr(self, '_is_cleaning_up', False):
            raise CommunicationError("Cannot read queues during cleanup")
        
        stdout_list = []
        stderr_list = []
        
        # 出力キューからの読み取り
        try:
            while True:
                try:
                    item = await asyncio.wait_for(
                        self._output_queue.get(),
                        timeout=timeout
                    )
                    
                    if item is None:  # 終了マーカー
                        break
                        
                    if isinstance(item, IPCMessage):
                        if item.type == MessageType.ERROR:
                            raise CommunicationError(
                                "Error message received",
                                direction="receive",
                                data=item.data
                            )
                        stdout_list.append(item.data)
                    else:
                        stdout_list.append(item)
                    
                    # 一定量のデータを読み取ったら終了
                    if len(stdout_list) >= 100:
                        break
                        
                except asyncio.TimeoutError:
                    # タイムアウトしたら現時点での結果を返す
                    break
        except Exception as e:
            self.logger.error(f"Error reading from output queue: {e}")
            raise CommunicationError(f"Error reading from output queue: {e}", direction="receive")
            
        # エラーキューからの読み取り
        try:
            while True:
                try:
                    item = await asyncio.wait_for(
                        self._error_queue.get(),
                        timeout=timeout / 2  # エラーキューは短めのタイムアウト
                    )
                    
                    if item is None:  # 終了マーカー
                        break
                        
                    if isinstance(item, IPCMessage):
                        stderr_list.append(item.data)
                    else:
                        stderr_list.append(item)
                        
                    # 一定量のデータを読み取ったら終了
                    if len(stderr_list) >= 50:
                        break
                        
                except asyncio.TimeoutError:
                    # タイムアウトしたら現時点での結果を返す
                    break
        except Exception as e:
            self.logger.error(f"Error reading from error queue: {e}")
            # エラーキューの読み取りエラーは無視して続行
            
        return stdout_list, stderr_list
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(CommunicationError)
    )
    async def _execute_raw(self, script: str) -> str:
        """
        スクリプトを実行し、生の出力を返します。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            コマンドの出力
        """
        if not self.process or not self.process.stdin:
            raise ProcessError("PowerShell process not initialized or already closed")
            
        if self.process.stdin.is_closing():
            raise ProcessError("PowerShell stdin is closed")
            
        # コマンドを送信
        try:
            self.logger.debug(f"Sending command: {script}")
            self._last_command = script
            
            # コマンドをエンコードして送信
            encoded_cmd = (script + "\n").encode()
            self.process.stdin.write(encoded_cmd)
            await self.process.stdin.drain()
            
        except Exception as e:
            self.logger.error(f"Error sending command: {e}")
            raise CommunicationError(
                f"コマンドの送信に失敗しました: {e}", 
                direction="send", 
                data=script
            )
            
        # 出力を読み取る
        outputs, errors = await self._read_queues(self._execution_timeout)
        
        if not outputs and not errors:
            raise CommunicationError(
                "コマンドからの応答がありません", 
                direction="receive", 
                data=script
            )
        
        # エラーがあれば例外をスロー
        if errors:
            self.logger.error(f"Command execution error: {errors}")
            error_msg = "\n".join(errors)
            raise PowerShellExecutionError(f"コマンド実行エラー: {error_msg}", details=script)
            
        # 結果を処理して返す
        return self._process_output(outputs)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ProcessError, PowerShellTimeoutError))
    )
    @as_async_result
    async def execute(self, command: str) -> Any:
        """
        PowerShellコマンドを実行します。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            コマンドの実行結果
        """
        if not self.process:
            raise ProcessError("PowerShell process not initialized")
            
        if self._stop_event.is_set():
            raise ProcessError("Session is shutting down")
            
        try:
            self.logger.debug(f"Executing command: {command}")
            result = await self._execute_raw(command)
            
            # 結果が SUCCESS または ERROR マーカーを含むか確認
            if "COMMAND_SUCCESS" in result:
                # 成功マーカーを削除
                result = result.replace("COMMAND_SUCCESS", "").strip()
                
                # JSONの場合はパース
                if result and (result.startswith('{') or result.startswith('[')):
                    try:
                        return json.loads(result)
                    except json.JSONDecodeError:
                        # JSONでない場合はそのまま返す
                        pass
                        
                return result
                
            elif "COMMAND_ERROR" in result:
                # エラーマーカーを含む場合はエラーとして処理
                result = result.replace("COMMAND_ERROR", "").strip()
                raise PowerShellExecutionError(f"PowerShellからエラー: {result}", details=command)
                
            # どちらのマーカーも含まない場合
            self.logger.warning(f"Command result doesn't contain success/error marker: {result}")
            return result
            
        except PowerShellTimeoutError:
            self.logger.error(f"Command execution timed out: {command}")
            raise
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            if isinstance(e, PowerShellError):
                raise
            else:
                raise PowerShellExecutionError(f"コマンド実行中にエラーが発生しました: {e}", details=command)
    
    def _process_output(self, outputs: list) -> str:
        """
        出力を処理して単一の文字列に結合します。
        
        Args:
            outputs: 出力のリスト
            
        Returns:
            処理済みの出力文字列
        """
        if not outputs:
            return ""
            
        # リスト内の各要素を文字列に変換して結合
        result = []
        for item in outputs:
            if isinstance(item, IPCMessage):
                result.append(str(item.data))
            else:
                result.append(str(item))
                
        return "\n".join(result)
    
    async def _cleanup_resources(self):
        """関連リソースのクリーンアップ処理を実行します。"""
        # 読み込みイベントを停止
        self._stop_event.set()
        
        # 標準入出力ストリームをクローズ
        if self.process:
            try:
                if self.process.stdin and not self.process.stdin.is_closing():
                    self.process.stdin.close()
                    
                # stdout/stderrは読み取り専用なので明示的にclose不要
            except Exception as e:
                self.logger.error(f"標準入出力のクローズに失敗: {e}")
                
        # プロセスの強制終了 (まだ実行中の場合)
        try:
            if self.process:
                # プロセスのステータスを取得
                if hasattr(self.process, "returncode") and self.process.returncode is None:
                    # まだ終了していない
                    self.process.kill()
                    
            # psutilプロセスも確認
            if self._ps_process and self._ps_process.is_running():
                try:
                    self._ps_process.kill()
                except psutil.NoSuchProcess:
                    pass  # すでに終了している
                except Exception as e:
                    self.logger.error(f"psutilプロセスの終了に失敗: {e}")
        except Exception as e:
            self.logger.error(f"プロセスのクリーンアップに失敗: {e}")
            
        # キューをクリア
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except:
                pass
                
        while not self._error_queue.empty():
            try:
                self._error_queue.get_nowait()
            except:
                pass
                
        # プロセスマネージャーのクリーンアップ
        await self._process_manager.cleanup()
        
        self.logger.debug("リソースのクリーンアップ完了")
    
    async def _wait_for_ready(self) -> None:
        """PowerShellセッションが準備完了状態になるまで待機します。"""
        self.logger.debug("Waiting for PowerShell session to be ready")
        
        ready = False
        start_time = time.time()
        
        while not ready and time.time() - start_time < self._startup_timeout:
            # キャンセルされた場合は中断
            if self._stop_event.is_set():
                raise ProcessError("Session initialization cancelled")
                
            try:
                # 出力を読み取る
                outputs, errors = await self._read_queues(timeout=1.0)
                
                # エラーがあれば例外をスロー
                if errors:
                    error_msg = "\n".join(errors)
                    raise ProcessError(f"Error during session initialization: {error_msg}")
                    
                # 準備完了マーカーを確認
                for output in outputs:
                    if "SESSION_READY" in str(output):
                        ready = True
                        break
                        
                # まだ準備ができていなければ少し待機
                if not ready:
                    await asyncio.sleep(0.1)
                    
            except asyncio.TimeoutError:
                # タイムアウトしたら再試行
                continue
            except Exception as e:
                self.logger.error(f"Error waiting for session ready: {e}")
                raise ProcessError(f"Session initialization error: {e}")
                
        if not ready:
            raise PowerShellTimeoutError("Session initialization timed out")
            
        self.logger.debug("PowerShell session is ready")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_exception_type((ProcessError, PowerShellTimeoutError))
    )
    async def restart(self):
        """PowerShellセッションを再起動します。"""
        self.logger.info("PowerShellセッションを再起動しています")
        
        # 既存のセッションをクリーンアップ
        await self._cleanup_resources()
        
        # プロセス状態をリセット
        self.process = None
        self._ps_process = None
        self._stop_event.clear()
        
        try:
            # 新しいプロセスを開始
            await asyncio.wait_for(
                self._start_powershell_process(),
                timeout=self._startup_timeout
            )
            
            # 読み取りタスクを再開
            self._start_io_tasks()
            
            # 初期化完了を待機
            await asyncio.wait_for(
                self._wait_for_ready(),
                timeout=self._startup_timeout
            )
            
            self.logger.info("PowerShellセッションの再起動が完了しました")
        except asyncio.TimeoutError:
            self.logger.error("PowerShellセッションの再起動がタイムアウトしました")
            raise PowerShellTimeoutError("PowerShellセッションの再起動がタイムアウトしました")
        except Exception as e:
            self.logger.error(f"PowerShellセッションの再起動に失敗しました: {e}")
            raise PowerShellError.from_exception(e, "PowerShellセッションの再起動に失敗しました") 