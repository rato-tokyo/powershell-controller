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
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..errors import (
    PowerShellError,
    PowerShellTimeoutError,
    PowerShellExecutionError,
    ProcessError,
    CommunicationError
)
from ...infra.async_utils.process import AsyncProcessManager
from ...infra.async_utils.test_helper import AsyncTestHelper
from ...infra.ipc.protocol import IPCMessage, IPCProtocol, MessageType
from .base import BaseSession

class PowerShellSession(BaseSession):
    """PowerShellセッションを管理するコンテキストマネージャ"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, timeout: float = 30.0):
        """
        PowerShellセッションを初期化します。
        
        Args:
            config: PowerShellの設定。Noneの場合はデフォルト設定を使用。
            timeout: タイムアウト時間（秒）
        """
        super().__init__(timeout)
        self.config = config or {"log_level": "ERROR"}
        self.process: Optional[asyncio.subprocess.Process] = None
        self._ps_process: Optional[psutil.Process] = None
        self._output_queue: asyncio.Queue = asyncio.Queue()
        self._error_queue: asyncio.Queue = asyncio.Queue()
        self._process_manager = AsyncProcessManager()
        self._startup_timeout = 10.0  # プロセス起動用のタイムアウト（短縮）
        self._execution_timeout = 5.0  # コマンド実行用のタイムアウト（短縮）
        self._read_timeout = 0.5  # キュー読み取り用のタイムアウト（短縮）
        self._last_command: str = ""  # 最後に実行したコマンド
        self.logger = logger.bind(module="powershell_session")
        
    async def __aenter__(self) -> 'PowerShellSession':
        """セッションを開始します。"""
        try:
            # イベントループを取得
            self._loop = asyncio.get_event_loop()
            
            # PowerShellプロセスを起動
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            # 非同期プロセスを作成
            async def create_process():
                # PowerShellのパスを取得
                powershell_path = "powershell.exe"
                if os.path.exists("C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"):
                    powershell_path = "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
                
                # 環境変数を設定
                env = os.environ.copy()
                env.update({
                    "POWERSHELL_TELEMETRY_OPTOUT": "1",  # テレメトリを無効化
                    "PSModulePath": "",  # モジュールパスをクリア
                    "PATHEXT": ".COM;.EXE;.BAT;.CMD",  # 基本的な実行ファイル拡張子のみ
                    "POWERSHELL_UPDATECHECK": "Off",  # 更新チェックを無効化
                    "POWERSHELL_MANAGED_MODE": "Off",  # マネージドモードを無効化
                    "POWERSHELL_BASIC_MODE": "On",  # 基本モードを有効化
                    "POWERSHELL_DISABLE_EXTENSIONS": "1"  # 拡張機能を無効化
                })
                
                # 初期化コマンド
                init_command = """
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "PowerShell Controller Session"
Write-Output "SESSION_READY"
While ($true) {
    $command = Read-Host
    if ($command -eq "EXIT") { break }
    try {
        $result = Invoke-Expression -Command $command -ErrorAction Stop
        if ($null -ne $result) {
            try {
                # JSON変換を試みるが、失敗したら普通の文字列として出力
                $json = ConvertTo-Json -InputObject $result -Depth 5 -Compress -ErrorAction SilentlyContinue
                if ($null -ne $json) {
                    Write-Output $json
                } else {
                    Write-Output $result.ToString()
                }
            } catch {
                Write-Output $result.ToString()
            }
        }
        Write-Output "COMMAND_SUCCESS"
    } catch {
        $errorMessage = $_.Exception.Message
        Write-Error "ERROR: $errorMessage"
        Write-Output "COMMAND_ERROR"
    }
}
Write-Output "SESSION_END"
"""
                # 対話モードでプロセスを起動（高速起動オプション追加）
                self.logger.debug(f"Starting PowerShell process: {powershell_path}")
                process = await asyncio.create_subprocess_exec(
                    powershell_path,
                    "-Version", "5.1",
                    "-NoLogo",
                    "-NoProfile", 
                    "-ExecutionPolicy", "Bypass",
                    "-NoExit",  # プロセスが終了しないようにする
                    "-Command", init_command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    startupinfo=startupinfo,
                    env=env
                )
                
                if not process or not process.pid:
                    raise ProcessError("Failed to start PowerShell process")
                
                self.logger.debug(f"PowerShell process started with PID: {process.pid}")
                return process
                
            try:
                # プロセスを作成
                self.process = await asyncio.wait_for(
                    create_process(),
                    timeout=self._startup_timeout
                )
                self.logger.info(f"PowerShell process started with PID {self.process.pid}")
                
            except asyncio.TimeoutError:
                raise PowerShellTimeoutError(f"PowerShellセッションの初期化がタイムアウトしました（{self._startup_timeout}秒）")
            
            # psutilプロセスを取得
            if self.process and self.process.pid:
                self._ps_process = psutil.Process(self.process.pid)
                if not self._ps_process.is_running():
                    raise ProcessError("PowerShell process failed to start")
                
            # 出力とエラーの読み取りタスクを開始
            self._start_io_tasks()
            
            # 初期化完了を待機
            try:
                await asyncio.wait_for(
                    self._wait_for_ready(),
                    timeout=10.0
                )
                self.logger.info("PowerShell session initialized successfully")
            except asyncio.TimeoutError:
                raise PowerShellTimeoutError("PowerShell session initialization timed out")
            except Exception as e:
                raise ProcessError(f"Failed to initialize PowerShell session: {e}")
            
            return self
            
        except Exception as e:
            self.logger.error(f"Error during PowerShell session initialization: {e}")
            await self._cleanup_resources()
            raise
            
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """セッションを終了します。"""
        self._stop_event.set()
        
        if self.process:
            try:
                self.process.terminate()
                async def wait_process():
                    await self.process.wait()
                    
                try:
                    await self._process_manager.run_in_executor(
                        wait_process,
                        timeout=5.0,
                        task_id="ps_process_termination"
                    )
                except PowerShellTimeoutError:
                    if self.process:
                        self.process.kill()
                        
            except Exception as e:
                self.logger.error(f"Error during PowerShell process termination: {e}")
            finally:
                self.process = None
                self._ps_process = None
                
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((CommunicationError, ProcessError))
    )
    async def _read_queues(self, timeout: float = None) -> Tuple[List[str], List[str]]:
        """
        出力キューとエラーキューから読み取りを行います。
        tenacityを使用して自動リトライ機能を追加しています。
        
        Args:
            timeout: タイムアウト時間（秒）
            
        Returns:
            (出力リスト, エラーリスト)のタプル
        """
        if timeout is None:
            timeout = self._read_timeout
            
        output_lines = []
        error_lines = []
        
        try:
            # 出力キューから読み取り
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    output = await asyncio.wait_for(self._output_queue.get(), timeout=0.1)
                    if output is None:  # 終了マーカー
                        break
                    output_lines.append(output)
                    # 実行結果のマーカーを検出したら即終了
                    if "COMMAND_SUCCESS" in output or "SESSION_READY" in output:
                        break
                except asyncio.TimeoutError:
                    # 何かしらの出力を受け取った後で一定時間出力がなければ終了
                    if output_lines:
                        break
                    continue
                    
            # エラーキューから読み取り
            error_check_time = min(0.5, timeout / 2)  # エラーチェックは短めに
            start_time = time.time()
            while time.time() - start_time < error_check_time:
                try:
                    error = await asyncio.wait_for(self._error_queue.get(), timeout=0.1)
                    if error is None:  # 終了マーカー
                        break
                    error_lines.append(error)
                except asyncio.TimeoutError:
                    break
                    
        except Exception as e:
            self.logger.error(f"Error reading queues: {e}")
            
        return output_lines, error_lines
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(CommunicationError)
    )
    async def _execute_raw(self, script: str) -> str:
        """
        生のPowerShellスクリプトを実行します。
        tenacityを使用して自動リトライ機能を追加しています。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            実行結果の文字列
        """
        if not self.process or not self.process.stdin:
            raise ProcessError("PowerShell process is not running")
            
        try:
            # コマンドをエスケープして標準入力に送信
            escaped_script = script.replace("\n", " ").strip()
            command_with_newline = f"{escaped_script}\n"
            
            # スクリプトを送信
            self.process.stdin.write(command_with_newline.encode("utf-8"))
            await self.process.stdin.drain()
            
            # 出力を待機（短いタイムアウトを使用）
            output_lines, error_lines = await self._read_queues(timeout=self._execution_timeout)
            
            if error_lines:
                error_message = "\n".join(error_lines)
                raise PowerShellExecutionError(error_message)
                
            return "\n".join(output_lines)
            
        except Exception as e:
            error_msg = f"Failed to execute PowerShell script: {e}"
            self.logger.error(error_msg)
            raise PowerShellError(error_msg)
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ProcessError, PowerShellTimeoutError))
    )
    async def execute(self, command: str) -> str:
        """
        コマンドを実行して結果を返します。
        tenacityを使用して自動リトライ機能を実装しています。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            コマンドの実行結果
            
        Raises:
            PowerShellError: PowerShellでエラーが発生した場合
            PowerShellTimeoutError: タイムアウトの場合
            ProcessError: プロセスエラーの場合
        """
        self.logger.debug(f"Executing command: {command}")
        self._last_command = command  # コマンドを記録
        
        if not self.process or self.process.returncode is not None:
            error_msg = "PowerShellプロセスが実行されていません"
            self.logger.error(error_msg)
            raise ProcessError(error_msg)
            
        if not self.process.stdin or self.process.stdin.is_closing():
            error_msg = "PowerShellの標準入力が利用できません"
            self.logger.error(error_msg)
            raise ProcessError(error_msg)
            
        try:
            # コマンドを実行
            command_bytes = f"{command}\n".encode()
            self.process.stdin.write(command_bytes)
            await self.process.stdin.drain()
            
            # 応答を待機
            outputs, errors = await self._read_queues(timeout=self.timeout)
            
            # エラーチェック
            if errors:
                error_msg = "\n".join(errors)
                self.logger.error(f"PowerShellエラー: {error_msg}")
                # PowerShellエラーとして処理
                raise ProcessError(f"PowerShellエラー: {error_msg}")
                
            # 成功の場合は結果を返す
            result = self._process_output(outputs)
            self.logger.debug(f"Command executed successfully: {result}")
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"コマンド実行がタイムアウトしました: {command}"
            self.logger.error(error_msg)
            raise PowerShellTimeoutError(error_msg)
            
        except Exception as e:
            if isinstance(e, (PowerShellTimeoutError, ProcessError)):
                raise
            error_msg = f"コマンド実行中にエラーが発生しました: {e}"
            self.logger.error(error_msg)
            raise ProcessError(error_msg) from e
            
    def _process_output(self, outputs: list) -> str:
        """
        コマンド実行の出力を処理します。
        
        Args:
            outputs: 出力のリスト
            
        Returns:
            処理された出力
        """
        if not outputs:
            return ""
            
        # コマンド自体と"COMMAND_SUCCESS"を除外する
        filtered_outputs = []
        for output in outputs:
            # コマンド自体をスキップ
            if output == self._last_command:
                continue
                
            # 成功マーカーをスキップ
            if output == "COMMAND_SUCCESS":
                continue
                
            filtered_outputs.append(output)
            
        # 文字列を結合（結果が1つの場合はそのまま返す）
        if len(filtered_outputs) == 1:
            # 引用符で囲まれている場合は引用符を削除
            result = filtered_outputs[0]
            if result.startswith('"') and result.endswith('"'):
                result = result[1:-1]
            return result
            
        return "\n".join(filtered_outputs)

    async def _cleanup_resources(self):
        """リソースをクリーンアップします。"""
        self.logger.debug("Cleaning up PowerShell session resources")
        
        # 停止イベントを設定
        self._stop_event.set()
        
        if self.process:
            try:
                # まずEXITコマンドを送信してPowerShellを正常終了させる
                if self.process.stdin and not self.process.stdin.is_closing():
                    try:
                        self.process.stdin.write(b"EXIT\n")
                        await asyncio.wait_for(self.process.stdin.drain(), timeout=2.0)
                    except (ConnectionError, BrokenPipeError, asyncio.TimeoutError):
                        self.logger.warning("Failed to send EXIT command")
                    
                # プロセスを終了
                if self.process.returncode is None:  # プロセスがまだ実行中の場合
                    self.process.terminate()
                    
                    # プロセスの終了を待機
                    try:
                        await asyncio.wait_for(self.process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        self.logger.warning("Process termination timed out, forcing kill")
                        self.process.kill()
                        try:
                            await asyncio.wait_for(self.process.wait(), timeout=2.0)
                        except asyncio.TimeoutError:
                            self.logger.error("Failed to kill process after timeout")
                    
            except Exception as e:
                self.logger.error(f"Error during process cleanup: {e}")
            finally:
                self.process = None
                
        # psutilプロセスのクリーンアップ
        if self._ps_process:
            try:
                if self._ps_process.is_running():
                    try:
                        self._ps_process.terminate()
                        try:
                            self._ps_process.wait(timeout=5.0)
                        except psutil.TimeoutExpired:
                            self._ps_process.kill()
                            try:
                                self._ps_process.wait(timeout=2.0)
                            except psutil.TimeoutExpired:
                                self.logger.error("Failed to kill psutil process")
                    except psutil.NoSuchProcess:
                        pass
            except Exception as e:
                self.logger.error(f"Error during psutil process cleanup: {e}")
            finally:
                self._ps_process = None
                
        # キューのクリーンアップ
        try:
            # 読み込みが停止するのを少し待つ
            await asyncio.sleep(0.5)
            
            while not self._output_queue.empty():
                await self._output_queue.get()
            while not self._error_queue.empty():
                await self._error_queue.get()
        except Exception as e:
            self.logger.error(f"Error during queue cleanup: {e}")
            
        # プロセスマネージャのクリーンアップ
        try:
            await self._process_manager.cleanup()
        except Exception as e:
            self.logger.error(f"Error during process manager cleanup: {e}")
            
        self.logger.debug("PowerShell session resources cleaned up")

    async def _wait_for_ready(self) -> None:
        """PowerShellセッションの初期化完了を待機します。"""
        # 最大5秒間だけ待機
        max_wait_time = 5.0
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                output_lines, error_lines = await self._read_queues(timeout=0.5)
                if "SESSION_READY" in output_lines:
                    return
                if error_lines:
                    raise PowerShellError("\n".join(error_lines))
                # 短い間隔で再試行
                await asyncio.sleep(0.1)
            except asyncio.TimeoutError:
                continue
                
        # タイムアウト後も SESSION_READY が見つからない場合
        raise PowerShellTimeoutError("PowerShell session initialization timed out")

    @retry(
        stop=stop_after_attempt(2),  # リトライ回数を減らす
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),  # 待機時間を短縮
        retry=retry_if_exception_type((ProcessError, PowerShellTimeoutError))
    )
    async def restart(self):
        """
        PowerShellセッションを再起動します。
        tenacityを使用して自動リトライ機能を実装しています。
        """
        self.logger.info("Restarting PowerShell session...")
        
        # 既存のリソースをクリーンアップ
        await self._cleanup_resources()
        
        # 状態をリセット
        self._stop_event.clear()
        self._is_cleaning_up = False
        self._output_queue = asyncio.Queue()
        self._error_queue = asyncio.Queue()
        
        # 新しいプロセスを起動
        try:
            # イベントループを取得
            self._loop = asyncio.get_event_loop()
            
            # PowerShellプロセスを起動
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # 簡易版のプロセス作成（フルバージョンよりも高速）
            powershell_path = "powershell.exe"
            if os.path.exists("C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"):
                powershell_path = "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
            
            # 環境変数を簡易化（必要なものだけ）
            env = os.environ.copy()
            env.update({
                "POWERSHELL_TELEMETRY_OPTOUT": "1",
                "PSModulePath": "",
                "POWERSHELL_UPDATECHECK": "Off"
            })
            
            # 初期化コマンド（シンプル版）
            init_command = """
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
Write-Output "SESSION_READY"
While ($true) {
    $command = Read-Host
    if ($command -eq "EXIT") { break }
    try {
        $result = Invoke-Expression -Command $command -ErrorAction Stop
        if ($null -ne $result) { 
            Write-Output $result.ToString() 
        }
        Write-Output "COMMAND_SUCCESS"
    } catch {
        Write-Error "ERROR: $_"
        Write-Output "COMMAND_ERROR"
    }
}
"""
            # プロセスを作成（短いタイムアウトで）
            self.process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    powershell_path,
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-NoExit",
                    "-Command", init_command,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    startupinfo=startupinfo,
                    env=env
                ),
                timeout=5.0  # 短いタイムアウト
            )
            
            self.logger.info(f"PowerShell process restarted with PID {self.process.pid}")
            
            # psutilプロセスを取得
            if self.process and self.process.pid:
                self._ps_process = psutil.Process(self.process.pid)
                if not self._ps_process.is_running():
                    raise ProcessError("PowerShell process failed to start")
            
            # 出力とエラーの読み取りタスクを開始
            self._start_io_tasks()
            
            # 初期化完了を待機（短いタイムアウト）
            try:
                await asyncio.wait_for(
                    self._wait_for_ready(),
                    timeout=3.0  # さらに短いタイムアウト
                )
                self.logger.info("PowerShell session restarted successfully")
            except asyncio.TimeoutError:
                raise PowerShellTimeoutError("PowerShell session restart timed out")
            except Exception as e:
                raise ProcessError(f"Failed to restart PowerShell session: {e}")
                
        except Exception as e:
            error_msg = f"Failed to restart PowerShell session: {e}"
            self.logger.error(error_msg)
            raise ProcessError(error_msg) 