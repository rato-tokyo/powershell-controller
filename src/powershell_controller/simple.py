"""
シンプルなPowerShell 7コントローラー
MCPのためのセッション管理とコマンド実行に特化
"""
import subprocess
import os
import sys
import logging
import tempfile
import uuid
import time
import psutil
import json
import structlog
from logging.handlers import RotatingFileHandler

# structlogの設定
def setup_structlog(log_level=logging.INFO, log_file=None, max_log_size=10*1024*1024, test_handler=None):
    """
    structlogの設定を行う
    
    Args:
        log_level: ログレベル
        log_file: ログファイルのパス
        max_log_size: ログファイルの最大サイズ
        test_handler: テスト用のログハンドラー（オプション）
        
    Returns:
        structlog.BoundLogger: 設定済みのstructlogロガー
    """
    # 基本的なロガーの設定
    logging.basicConfig(level=log_level, format='%(message)s')
    
    # 既存のハンドラーをクリア
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    
    # 標準出力へのハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # ファイルへのハンドラー（指定された場合）
    if log_file:
        try:
            # ログディレクトリが存在しない場合は作成
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # 通常のFileHandlerを使用
            file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
            file_handler.setLevel(log_level)
            root_logger.addHandler(file_handler)
            
            # テスト用のログファイル作成確認
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "event": "log_file_initialized",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "log_file": log_file
                }) + "\n")
                
        except Exception as e:
            print(f"Error setting up log file: {e}")
    
    # structlogの設定
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # テストハンドラーが指定されている場合は追加
    if test_handler:
        # テストハンドラーをstructlogに接続
        structlog.configure(
            processors=[
                # 既存のプロセッサを保持
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                test_handler,  # テストハンドラーを追加
                structlog.processors.JSONRenderer(sort_keys=True),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    logger = structlog.get_logger(__name__)
    
    # ログファイルが指定されている場合、直接書き込む
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "event": "powershell_init_start",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                }) + "\n")
        except Exception as e:
            print(f"Error writing to log file: {e}")
    
    return logger

class PowerShellError(Exception):
    """PowerShell実行に関連するエラーの基底クラス"""
    pass

class PowerShellNotFoundError(PowerShellError):
    """PowerShell 7が見つからない場合のエラー"""
    pass

class PowerShellExecutionError(PowerShellError):
    """PowerShellコマンドの実行に失敗した場合のエラー"""
    def __init__(self, message, command=None, stderr=None):
        super().__init__(message)
        self.command = command
        self.stderr = stderr

class PowerShellTimeoutError(PowerShellError):
    """PowerShellコマンドがタイムアウトした場合のエラー"""
    pass

class SimplePowerShellController:
    """PowerShell 7のセッション管理とコマンド実行を行うコントローラー"""
    
    def __init__(self, log_level=logging.INFO, log_file=None, max_log_size=10*1024*1024, test_handler=None):
        """
        PowerShell 7コントローラーを初期化
        
        Args:
            log_level: ログレベル（デフォルト：INFO）
            log_file: ログファイルのパス（デフォルト：None）
            max_log_size: ログファイルの最大サイズ（デフォルト：10MB）
            test_handler: テスト用のログハンドラー（オプション）
        """
        # ログ設定を初期化
        self.logger = setup_structlog(log_level, log_file, max_log_size, test_handler)
        self.log_file = log_file
        self.ps_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
        self.process = None
        self.pid = None
        
        if not os.path.exists(self.ps_path):
            self._write_log("powershell_not_found", {"error": "PowerShell 7が見つかりません", "path": self.ps_path})
            raise FileNotFoundError(f"PowerShell 7が見つかりません: {self.ps_path}")
            
        try:
            result = self._run_simple_command("Write-Output 'PowerShell 7 Test'")
            
            if "PowerShell 7 Test" not in result:
                self._write_log("powershell_init_failed", {"error": "PowerShell 7の動作確認に失敗しました", "result": result})
                raise RuntimeError("PowerShell 7の動作確認に失敗しました")
            
            self._write_log("powershell_init_complete", {"result": result})
            
        except Exception as e:
            self._write_log("powershell_init_error", {"error": str(e)})
            raise
    
    def _write_log(self, event, data=None):
        """ログを書き込む（ファイルとstructlogの両方）"""
        # structlogでログを出力
        data = data or {}
        if event == "powershell_not_found":
            self.logger.error(event, **data)
        elif event == "powershell_init_failed" or event == "powershell_init_error":
            self.logger.error(event, **data)
        else:
            self.logger.info(event, **data)
        
        # ログファイルが指定されている場合、直接書き込む
        if self.log_file:
            try:
                log_entry = {
                    "event": event,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                log_entry.update(data or {})
                
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                print(f"Error writing to log file: {e}")

    def _cleanup_process(self):
        """
        プロセスをクリーンアップ
        
        子プロセスも含めて確実に終了させる
        """
        if self.pid is None:
            return

        try:
            process = psutil.Process(self.pid)
            
            # 子プロセスを取得して終了
            children = process.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            
            # メインプロセスを終了
            process.terminate()
            
            # プロセスの終了を待機
            gone, alive = psutil.wait_procs([process] + children, timeout=3)
            
            # 残っているプロセスを強制終了
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
                
            self._write_log("process_cleanup_complete", {"pid": self.pid})
            
        except psutil.NoSuchProcess:
            self._write_log("process_already_terminated", {"pid": self.pid})
        except Exception as e:
            self._write_log("process_cleanup_error", {"pid": self.pid, "error": str(e)})
        finally:
            self.pid = None
            self.process = None
    
    def _run_simple_command(self, command, timeout=10):
        """
        シンプルなコマンド実行
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: タイムアウト時間（秒）
            
        Returns:
            str: コマンドの出力
            
        Raises:
            PowerShellExecutionError: コマンド実行に失敗した場合
            PowerShellTimeoutError: タイムアウトした場合
        """
        self._write_log("command_execution_start", {"command": command, "timeout": timeout})
            
        start_time = time.time()
        
        try:
            self.process = subprocess.Popen(
                [self.ps_path, "-NoProfile", "-NonInteractive", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            self.pid = self.process.pid
            
            self._write_log("process_started", {"pid": self.pid, "command": command})
            
            stdout, stderr = self.process.communicate(timeout=timeout)
            execution_time = time.time() - start_time
            
            if self.process.returncode != 0:
                self._write_log("command_execution_failed", {
                    "command": command,
                    "error": stderr,
                    "return_code": self.process.returncode,
                    "execution_time": execution_time
                })
                    
                raise PowerShellExecutionError(
                    f"PowerShellコマンドの実行に失敗: {stderr}",
                    command=command,
                    stderr=stderr
                )
            
            self._write_log("command_execution_complete", {
                "command": command,
                "execution_time": execution_time,
                "output": stdout.strip()
            })
                
            return stdout.strip()
            
        except subprocess.TimeoutExpired:
            self._write_log("command_timeout", {
                "command": command,
                "timeout": timeout,
                "execution_time": time.time() - start_time
            })
                
            raise PowerShellTimeoutError(
                f"PowerShellコマンドがタイムアウト（{timeout}秒）: {command}"
            )
            
        except Exception as e:
            self._write_log("command_execution_error", {
                "command": command,
                "error": str(e),
                "execution_time": time.time() - start_time
            })
                
            raise
            
        finally:
            self._cleanup_process()

    def execute_command(self, command, timeout=10):
        """
        PowerShellコマンドを実行
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: タイムアウト時間（秒）
            
        Returns:
            str: コマンドの出力
            
        Raises:
            PowerShellExecutionError: コマンド実行に失敗した場合
            PowerShellTimeoutError: タイムアウトした場合
        """
        # PowerShellスクリプトテンプレート
        ps_script = f"""
            try {{
                $ErrorActionPreference = 'Stop'
                $OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
                $ProgressPreference = 'SilentlyContinue'
                
                # 結果を格納するオブジェクト
                $outputObj = @{{
                    Success = $true
                    Output = $null
                    Error = $null
                }}
                
                try {{
                    # コマンドの実行
                    $result = {command}
                    
                    # 結果の処理
                    if ($null -ne $result) {{
                        # オブジェクトの場合はJSON形式に変換
                        if ($result -is [System.Management.Automation.PSObject] -or $result -is [Array] -or $result -is [System.Collections.Hashtable]) {{
                            $outputObj.Output = $result | ConvertTo-Json -Depth 10 -Compress
                        }}
                        else {{
                            # その他の場合は文字列として処理
                            $outputObj.Output = $result.ToString()
                        }}
                    }}
                }}
                catch {{
                    $outputObj.Success = $false
                    $outputObj.Error = @{{
                        Message = $_.Exception.Message
                        Category = $_.CategoryInfo.Category
                        FullyQualifiedErrorId = $_.FullyQualifiedErrorId
                        ScriptStackTrace = $_.ScriptStackTrace
                        PositionMessage = $_.InvocationInfo.PositionMessage
                    }}
                }}
                
                # 最終結果をJSON形式で出力
                $outputObj | ConvertTo-Json -Depth 10 -Compress
            }} catch {{
                # PowerShellエンジン自体のエラー
                @{{
                    Success = $false
                    Output = $null
                    Error = @{{
                        Message = $_.Exception.Message
                        Category = "EngineError"
                        FullyQualifiedErrorId = $null
                        ScriptStackTrace = $null
                        PositionMessage = $null
                    }}
                }} | ConvertTo-Json -Compress
                exit 1
            }}
            """
            
        self._write_log("command_execution_start", {"command": command})
        
        try:
            output = self._run_simple_command(ps_script, timeout)
            result = json.loads(output)
            
            if not result["Success"]:
                error_info = result["Error"]
                self._write_log("command_execution_failed", {
                    "command": command,
                    "error": error_info["Message"],
                    "error_info": error_info
                })
                raise PowerShellExecutionError(
                    error_info["Message"],
                    command=command,
                    stderr=error_info
                )
            
            output = result["Output"]
            # JSONエスケープされた文字列を元に戻す
            if isinstance(output, str):
                try:
                    # PowerShellオブジェクトの場合はJSONとして解析
                    if output.startswith("{") or output.startswith("["):
                        output = json.loads(output)
                    # 通常の文字列の場合は引用符を除去
                    elif output.startswith('"') and output.endswith('"'):
                        output = output[1:-1]
                except json.JSONDecodeError:
                    pass
            
            # 辞書型やリストの場合はJSON文字列に変換
            if isinstance(output, (dict, list)):
                output = json.dumps(output)
            
            self._write_log("command_execution_complete", {"command": command})
            return output
            
        except json.JSONDecodeError as e:
            self._write_log("json_decode_error", {
                "command": command,
                "error": str(e),
                "output": output
            })
            raise PowerShellExecutionError(f"JSON解析エラー: {str(e)}", command=command)
            
        except PowerShellTimeoutError:
            self._write_log("command_timeout", {
                "command": command,
                "timeout": timeout
            })
            raise
            
        except Exception as e:
            self._write_log("command_execution_error", {
                "command": command,
                "error": str(e)
            })
            raise

    def execute_commands_in_session(self, commands, timeout=30):
        """
        複数のコマンドをセッション内で実行
        
        Args:
            commands: 実行するPowerShellコマンドのリスト
            timeout: セッション全体のタイムアウト時間（秒）
            
        Returns:
            list: 各コマンドの実行結果
        """
        self._write_log("session_execution_start", {"command_count": len(commands)})
        results = []
        has_error = False
        
        try:
            for i, command in enumerate(commands):
                try:
                    result = self.execute_command(command, timeout)
                    results.append(result)
                except PowerShellExecutionError as e:
                    self._write_log("command_execution_failed", {
                        "command_index": i,
                        "error": str(e)
                    })
                    has_error = True
                    results.append(str(e))
                    continue
                    
            if has_error:
                self._write_log("session_completed_with_errors")
            else:
                self._write_log("session_execution_complete")
                
            return results
            
        except Exception as e:
            self._write_log("session_execution_error", {"error": str(e)})
            raise
            
        finally:
            self._cleanup_process()

    def __del__(self):
        """デストラクタ：プロセスのクリーンアップを確実に行う"""
        self._cleanup_process() 