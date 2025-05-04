"""
シンプルなPowerShell 7コントローラー
MCPのためのセッション管理とコマンド実行に特化
"""
import subprocess
import os
import sys
import tempfile
import uuid
import time
import psutil
import json
from loguru import logger

# Loguruのロギング設定
def setup_logging(log_level="INFO", log_file=None, test_handler=None):
    """
    Loguruを使ったロギング設定
    
    Args:
        log_level: ログレベル ("INFO", "DEBUG", "ERROR" など)
        log_file: ログファイルのパス
        test_handler: テスト用のログハンドラー（オプション）
        
    Returns:
        logger: 設定済みのLoguru logger
    """
    # 既存のハンドラーを削除
    logger.remove()
    
    # 標準出力へのロガー設定
    logger.add(sys.stdout, level=log_level, 
              format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}")
    
    # ログファイルへの出力設定
    if log_file:
        try:
            # ログディレクトリが存在しない場合は作成
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # ファイルにJSON形式でログを出力
            logger.add(
                log_file,
                level=log_level,
                format="{time:YYYY-MM-DDTHH:mm:ss.SSS}Z | {level} | {message}",
                rotation="10 MB",
                encoding="utf-8",
                serialize=True  # JSON形式で出力
            )
            
            # ログファイル初期化ログを直接書き込み
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "level": "INFO",
                    "event": "log_file_initialized",
                    "log_file": log_file
                }) + "\n")
                
        except Exception as e:
            print(f"Error setting up log file: {e}")
    
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
    
    def __init__(self, log_level="INFO", log_file=None, test_handler=None):
        """
        PowerShell 7コントローラーを初期化
        
        Args:
            log_level: ログレベル（デフォルト："INFO"）
            log_file: ログファイルのパス（デフォルト：None）
            test_handler: テスト用のログハンドラー（オプション）
                         entriesプロパティを持つオブジェクトが期待されます
        """
        # ログ設定を初期化
        self.logger = setup_logging(log_level, log_file)
        self.log_file = log_file
        self.ps_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
        self.process = None
        self.pid = None
        self.test_handler = test_handler
        
        if not os.path.exists(self.ps_path):
            self._log_event("powershell_not_found", {"error": "PowerShell 7が見つかりません", "path": self.ps_path}, "ERROR")
            raise FileNotFoundError(f"PowerShell 7が見つかりません: {self.ps_path}")
            
        try:
            result = self._run_simple_command("Write-Output 'PowerShell 7 Test'")
            
            if "PowerShell 7 Test" not in result:
                self._log_event("powershell_init_failed", {"error": "PowerShell 7の動作確認に失敗しました", "result": result}, "ERROR")
                raise RuntimeError("PowerShell 7の動作確認に失敗しました")
            
            self._log_event("powershell_init_complete", {"result": result})
            
        except Exception as e:
            self._log_event("powershell_init_error", {"error": str(e)}, "ERROR")
            raise
    
    def _log_event(self, event, data=None, level="INFO"):
        """
        イベントログを記録する
        
        Args:
            event: イベント名
            data: 追加データ（辞書形式）
            level: ログレベル（"INFO", "ERROR" など）
        """
        data = data or {}
        log_entry = {"event": event, **data}
        
        # loguruでログを記録
        if level == "ERROR":
            self.logger.error(json.dumps(log_entry))
        elif level == "WARNING":
            self.logger.warning(json.dumps(log_entry))
        elif level == "DEBUG":
            self.logger.debug(json.dumps(log_entry))
        else:
            self.logger.info(json.dumps(log_entry))
        
        # テストハンドラーにもログを記録 (存在する場合)
        if self.test_handler and hasattr(self.test_handler, "entries"):
            self.test_handler.entries.append(log_entry)
        
        # ログファイルが指定されている場合、直接書き込む（確実性のため）
        if self.log_file:
            try:
                log_entry["time"] = time.strftime("%Y-%m-%dT%H:%M:%S")
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
                
            self._log_event("process_cleanup_complete", {"pid": self.pid})
            
        except psutil.NoSuchProcess:
            self._log_event("process_already_terminated", {"pid": self.pid})
        except Exception as e:
            self._log_event("process_cleanup_error", {"pid": self.pid, "error": str(e)})
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
        self._log_event("command_execution_start", {"command": command, "timeout": timeout})
            
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
            
            self._log_event("process_started", {"pid": self.pid, "command": command})
            
            stdout, stderr = self.process.communicate(timeout=timeout)
            execution_time = time.time() - start_time
            
            if self.process.returncode != 0:
                self._log_event("command_execution_failed", {
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
            
            self._log_event("command_execution_complete", {
                "command": command,
                "execution_time": execution_time,
                "output": stdout.strip()
            })
                
            return stdout.strip()
            
        except subprocess.TimeoutExpired:
            self._log_event("command_timeout", {
                "command": command,
                "timeout": timeout,
                "execution_time": time.time() - start_time
            })
                
            raise PowerShellTimeoutError(
                f"PowerShellコマンドがタイムアウト（{timeout}秒）: {command}"
            )
            
        except Exception as e:
            self._log_event("command_execution_error", {
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
            
        self._log_event("command_execution_start", {"command": command})
        
        try:
            output = self._run_simple_command(ps_script, timeout)
            result = json.loads(output)
            
            if not result["Success"]:
                error_info = result["Error"]
                self._log_event("command_execution_failed", {
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
            
            self._log_event("command_execution_complete", {"command": command})
            return output
            
        except json.JSONDecodeError as e:
            self._log_event("json_decode_error", {
                "command": command,
                "error": str(e),
                "output": output
            })
            raise PowerShellExecutionError(f"JSON解析エラー: {str(e)}", command=command)
            
        except PowerShellTimeoutError:
            self._log_event("command_timeout", {
                "command": command,
                "timeout": timeout
            })
            raise
            
        except Exception as e:
            self._log_event("command_execution_error", {
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
        self._log_event("session_execution_start", {"command_count": len(commands)})
        results = []
        has_error = False
        
        try:
            for i, command in enumerate(commands):
                try:
                    result = self.execute_command(command, timeout)
                    results.append(result)
                except PowerShellExecutionError as e:
                    self._log_event("command_execution_failed", {
                        "command_index": i,
                        "error": str(e)
                    })
                    has_error = True
                    results.append(str(e))
                    continue
                    
            if has_error:
                self._log_event("session_completed_with_errors")
            else:
                self._log_event("session_execution_complete")
                
            return results
            
        except Exception as e:
            self._log_event("session_execution_error", {"error": str(e)})
            raise
            
        finally:
            self._cleanup_process()

    def __del__(self):
        """デストラクタ：プロセスのクリーンアップを確実に行う"""
        self._cleanup_process() 