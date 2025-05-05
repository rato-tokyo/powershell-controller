"""
シンプルなPowerShell 7コントローラー
MCPのためのセッション管理とコマンド実行に特化
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    TypedDict,
    TypeVar,
    Union,
)

import tenacity
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from result import Err, Ok, Result
from rich.console import Console
from rich.logging import RichHandler
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

# Richコンソールの初期化
console = Console()

class ValidatorInfo(TypedDict):
    """バリデータ情報の型定義"""
    data: Dict[str, Any]

def before_retry(retry_state: RetryCallState) -> None:
    """リトライ前の処理"""
    if retry_state.outcome is not None and retry_state.outcome.failed:
        logger.info(f"Retrying command after attempt {retry_state.attempt_number}")

def after_retry(retry_state: RetryCallState) -> None:
    """リトライ後の処理"""
    if retry_state.outcome is not None:
        if retry_state.outcome.failed:
            logger.warning(f"Retry attempt {retry_state.attempt_number} failed")
        else:
            logger.info(f"Retry attempt {retry_state.attempt_number} succeeded")

def retry_error_callback(retry_state: RetryCallState) -> None:
    """リトライエラー時の処理"""
    if retry_state.outcome is not None and retry_state.outcome.exception() is not None:
        logger.error(f"All retry attempts failed. Last error: {retry_state.outcome.exception()}")

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Loguruを使ったロギング設定（Richハンドラー使用）
    
    Args:
        log_level: ログレベル ("INFO", "DEBUG", "ERROR" など)
        log_file: ログファイルのパス
    """
    # 既存のハンドラーを削除
    logger.remove()

    # Richハンドラーを使用した標準出力へのロガー設定
    logger.add(
        RichHandler(console=console, rich_tracebacks=True),
        level=log_level,
        format="{message}"
    )

    # ファイルへのロギングが指定されている場合
    if log_file:
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
            rotation="1 day",
            retention="7 days"
        )

class PowerShellError(Exception):
    """PowerShell実行に関連するエラーの基底クラス"""
    pass

class PowerShellExecutionError(PowerShellError):
    """PowerShellコマンドの実行に失敗した場合のエラー"""
    def __init__(self, message: str, command: Optional[str] = None, stderr: Optional[str] = None, original_error: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.command = command
        self.stderr = stderr
        self.original_error = original_error

class PowerShellTimeoutError(PowerShellError):
    """PowerShellコマンドがタイムアウトした場合のエラー"""
    def __init__(self, message: str, command: Optional[str] = None) -> None:
        super().__init__(message)
        self.command = command

class RetryableError(PowerShellError):
    """リトライ可能なエラーを示す例外クラス"""
    def __init__(self, message: str, command: Optional[str] = None, stderr: Optional[str] = None) -> None:
        super().__init__(message)
        self.command = command
        self.stderr = stderr

class RetryConfig(BaseModel):
    """リトライ設定を定義するPydanticモデル"""
    max_attempts: int = Field(default=3, ge=1, description="最大リトライ回数")
    base_delay: float = Field(default=1.0, gt=0, description="基本待機時間（秒）")
    max_delay: float = Field(default=5.0, gt=0, description="最大待機時間（秒）")
    jitter: float = Field(default=0.1, ge=0, le=1, description="ジッターの割合")

    @field_validator('max_delay')
    @classmethod
    def max_delay_must_be_greater_than_base_delay(cls: Type[RetryConfig], v: float, info: Any) -> float:
        if hasattr(info, 'data') and 'base_delay' in info.data and v < info.data['base_delay']:
            raise ValueError('max_delayはbase_delay以上である必要があります')
        return v

class PowerShellControllerConfig(BaseModel):
    """PowerShellControllerの設定を定義するPydanticモデル"""
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_file: Optional[str] = None
    ps_path: str = Field(default=r"C:\Program Files\PowerShell\7\pwsh.exe")
    retry_config: RetryConfig = Field(default_factory=RetryConfig)

    @field_validator('ps_path')
    @classmethod
    def ps_path_must_exist(cls: Type[PowerShellControllerConfig], v: str) -> str:
        if not os.path.exists(v):
            raise ValueError(f'PowerShell実行ファイルが見つかりません: {v}')
        return v

class SimplePowerShellController:
    """PowerShell 7のセッション管理とコマンド実行を行うコントローラー"""

    def __init__(self, config: Optional[PowerShellControllerConfig] = None) -> None:
        """
        PowerShell 7コントローラーを初期化
        
        Args:
            config: コントローラーの設定（オプション）
        """
        self.config = config or PowerShellControllerConfig()
        setup_logging(self.config.log_level, self.config.log_file)
        self.process: Optional[subprocess.Popen[str]] = None
        self.pid: Optional[int] = None

        try:
            result = self._run_simple_command("Write-Output 'PowerShell 7 Test'")
            if result.is_err():
                error = result.unwrap_err()
                self._log_event("powershell_init_failed", {"error": str(error)}, "ERROR")
                raise error

            output = result.unwrap()
            if "PowerShell 7 Test" not in output:
                self._log_event(
                    "powershell_init_failed",
                    {"error": "PowerShell 7の動作確認に失敗しました", "result": output},
                    "ERROR"
                )
                raise RuntimeError("PowerShell 7の動作確認に失敗しました")

            self._log_event("powershell_init_complete", {"result": output})

        except Exception as e:
            self._log_event("powershell_init_error", {"error": str(e)}, "ERROR")
            raise

    def _log_event(self, event: str, data: Optional[Dict[str, Any]] = None, level: str = "INFO") -> None:
        """イベントをログに記録"""
        log_data = {
            "event": event,
            "timestamp": time.time(),
            **(data or {})
        }

        # ログレベルに応じてloguru loggerを使用
        getattr(logger, level.lower())(json.dumps(log_data))

    @retry(
        retry=retry_if_exception_type((RetryableError, subprocess.TimeoutExpired)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        before=before_retry,
        after=after_retry,
        retry_error_callback=retry_error_callback,
        reraise=False
    )
    def _run_simple_command(self, command: str, timeout: int = 10) -> Result[Union[str, Dict[str, Any], List[Any]], PowerShellError]:
        """
        シンプルなコマンド実行（リトライ機能付き）
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: タイムアウト時間（秒）
            
        Returns:
            Result[Union[str, Dict[str, Any], List[Any]], PowerShellError]: コマンドの実行結果
        """
        self._log_event("command_execution_start", {"command": command})

        try:
            process = subprocess.Popen(
                [self.config.ps_path, "-NoProfile", "-NonInteractive", "-Command", f"""
                try {{
                    $ErrorActionPreference = 'Stop'
                    $OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
                    $ProgressPreference = 'SilentlyContinue'
                    
                    # コマンドの実行
                    $result = {command}
                    
                    # 結果の処理
                    if ($null -ne $result) {{
                        # ハッシュテーブルやPSCustomObjectの場合は常にJSON形式で出力
                        if ($result -is [System.Collections.IDictionary] -or
                            $result -is [PSCustomObject] -or
                            $result -is [Array]) {{
                            Write-Output "JSON_START"
                            $result | ConvertTo-Json -Depth 10 -Compress
                            Write-Output "JSON_END"
                        }} else {{
                            # 通常の文字列出力
                            Write-Output $result.ToString()
                        }}
                    }}
                }} catch {{
                    $errorType = $_.Exception.GetType().Name
                    $errorMessage = $_.Exception.Message
                    $errorDetails = $_ | Format-List -Property * | Out-String
                    
                    Write-Host "ERROR_TYPE: $errorType" -ForegroundColor Red
                    Write-Host "ERROR_MESSAGE: $errorMessage" -ForegroundColor Red
                    Write-Host "ERROR_DETAILS: $errorDetails" -ForegroundColor Red
                    
                    if ($errorType -eq 'RuntimeException' -or
                        $errorMessage -match 'RuntimeException' -or
                        $errorMessage -match 'network error' -or
                        $errorMessage -match 'timeout' -or
                        $errorMessage -match 'connection') {{
                        exit 2  # リトライ可能なエラー
                    }} else {{
                        exit 1  # リトライ不可能なエラー
                    }}
                }}
                """],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )

            self.process = process
            self.pid = process.pid

            stdout, stderr = process.communicate(timeout=timeout)

            if process.returncode != 0:
                all_output = stdout + "\n" + stderr
                error_info = self._parse_error_output(all_output)
                error_msg = error_info.get('message', all_output.strip() if all_output else '不明なエラーが発生しました')
                error_type = error_info.get('type', 'Unknown')

                if process.returncode == 2:
                    return Err(RetryableError(
                        f"{error_type}: {error_msg}",
                        command=command,
                        stderr=all_output
                    ))
                else:
                    return Err(PowerShellExecutionError(
                        f"{error_type}: {error_msg}",
                        command=command,
                        stderr=all_output
                    ))

            return Ok(self._process_output(stdout))

        except subprocess.TimeoutExpired as e:
            if process:
                process.kill()
            return Err(RetryableError(
                "Command execution timed out",
                command=command,
                stderr=str(e)
            ))

        finally:
            if hasattr(self, 'process') and self.process:
                try:
                    self.process.kill()
                except Exception:
                    pass

    def _parse_error_output(self, stderr: str) -> Dict[str, str]:
        """PowerShellのエラー出力を解析"""
        error_info = {
            'type': 'Unknown',
            'message': '',
            'details': ''
        }

        if not stderr:
            return error_info

        stderr = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', stderr)
        stdout = stderr

        type_match = re.search(r'ERROR_TYPE:\s*(.+?)(?:\r?\n|$)', stdout)
        message_match = re.search(r'ERROR_MESSAGE:\s*(.+?)(?:\r?\n|$)', stdout)
        details_match = re.search(r'ERROR_DETAILS:\s*(.+?)(?:\r?\n|$)', stdout, re.DOTALL)

        if type_match:
            error_info['type'] = type_match.group(1).strip()
        if message_match:
            error_info['message'] = message_match.group(1).strip()
        if details_match:
            error_info['details'] = details_match.group(1).strip()

        if not error_info['message']:
            error_info['message'] = stderr.strip()

        return error_info

    def _process_output(self, output: str) -> Union[str, Dict[str, Any], List[Any]]:
        """PowerShellの出力を処理"""
        if not output:
            return ""
        
        # 出力から制御文字を削除
        output = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', output)
        output = output.strip()

        # JSON_START/JSON_ENDマーカーがある場合の処理
        if "JSON_START" in output and "JSON_END" in output:
            try:
                start_idx = output.index("JSON_START") + len("JSON_START")
                end_idx = output.index("JSON_END")
                json_str = output[start_idx:end_idx].strip()
                result = json.loads(json_str)
                if isinstance(result, list):
                    return [str(item) if not isinstance(item, (dict, list)) else item for item in result]
                return result
            except (ValueError, json.JSONDecodeError) as e:
                self._log_event("json_decode_error", {
                    "error": str(e),
                    "output": output
                }, "WARNING")
        
        # 直接JSON文字列として解析を試みる
        try:
            cleaned_output = output.strip()
            if (cleaned_output.startswith('{') and cleaned_output.endswith('}')) or \
               (cleaned_output.startswith('[') and cleaned_output.endswith(']')):
                result = json.loads(cleaned_output)
                if isinstance(result, list):
                    return [str(item) if not isinstance(item, (dict, list)) else item for item in result]
                return result
        except json.JSONDecodeError:
            pass

        # 改行を削除して再試行
        try:
            cleaned_output = re.sub(r'[\r\n\s]+', '', output)
            if (cleaned_output.startswith('{') and cleaned_output.endswith('}')) or \
               (cleaned_output.startswith('[') and cleaned_output.endswith(']')):
                result = json.loads(cleaned_output)
                if isinstance(result, list):
                    return [str(item) if not isinstance(item, (dict, list)) else item for item in result]
                return result
        except json.JSONDecodeError:
            pass
        
        return output

    def execute_command(self, command: str, timeout: int = 10) -> Union[str, Dict[str, Any], List[Any]]:
        """
        単一のPowerShellコマンドを実行
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: タイムアウト時間（秒）
            
        Returns:
            Union[str, Dict[str, Any], List[Any]]: コマンドの出力
            
        Raises:
            PowerShellExecutionError: コマンド実行に失敗した場合
            PowerShellTimeoutError: タイムアウトした場合
        """
        try:
            result = self._run_simple_command(command, timeout=timeout)
            if result.is_ok():
                return result.unwrap()
            else:
                error = result.unwrap_err()
                if isinstance(error, RetryableError):
                    if "timed out" in str(error) or "Timeout" in str(error):
                        raise PowerShellTimeoutError(
                            f"Command timed out after {timeout} seconds",
                            command=command
                        ) from error
                    else:
                        raise PowerShellExecutionError(
                            f"Command failed after {self.config.retry_config.max_attempts} retries: {str(error)}",
                            command=command,
                            stderr=error.stderr if hasattr(error, 'stderr') else str(error)
                        ) from error
                else:
                    raise error

        except tenacity.RetryError as retry_error:
            last_error = retry_error.last_attempt.exception()
            if isinstance(last_error, RetryableError):
                if "timed out" in str(last_error) or "Timeout" in str(last_error):
                    raise PowerShellTimeoutError(
                        f"Command timed out after {timeout} seconds and {self.config.retry_config.max_attempts} retries",
                        command=command
                    ) from last_error
                else:
                    raise PowerShellExecutionError(
                        f"Command failed after {self.config.retry_config.max_attempts} retries: {str(last_error)}",
                        command=command,
                        stderr=last_error.stderr if hasattr(last_error, 'stderr') else str(last_error)
                    ) from last_error
            else:
                raise PowerShellExecutionError(
                    f"Command failed after {self.config.retry_config.max_attempts} retries: {str(last_error)}",
                    command=command,
                    stderr=str(last_error)
                ) from last_error

    def execute_commands_in_session(self, commands: List[str], timeout: int = 10) -> List[Any]:
        """
        複数のPowerShellコマンドを同一セッションで実行
        
        Args:
            commands: 実行するPowerShellコマンドのリスト
            timeout: タイムアウト時間（秒）
            
        Returns:
            List[Any]: 各コマンドの出力のリスト
            
        Raises:
            PowerShellExecutionError: コマンド実行に失敗した場合
            PowerShellTimeoutError: タイムアウトした場合
        """
        script = """
            $ErrorActionPreference = 'Stop'
            $OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
            $ProgressPreference = 'SilentlyContinue'
            
            $results = @()
            
            {0}
            
            $results | ForEach-Object {{
                Write-Output "COMMAND_RESULT_START"
                if ($_ -is [System.Management.Automation.PSObject] -or
                    $_ -is [Array] -or
                    $_ -is [System.Collections.Hashtable]) {{
                    $jsonResult = $_ | ConvertTo-Json -Depth 10 -Compress
                    Write-Output $jsonResult
                }} else {{
                    Write-Output $_.ToString()
                }}
                Write-Output "COMMAND_RESULT_END"
            }}
        """.format('\n'.join(
            f"""
                try {{
                    $cmdResult = {cmd}
                    if ($null -ne $cmdResult) {{
                        $results += $cmdResult
                    }}
                }} catch {{
                    Write-Host "ERROR_TYPE: $($_.Exception.GetType().Name)" -ForegroundColor Red
                    Write-Host "ERROR_MESSAGE: $($_.Exception.Message)" -ForegroundColor Red
                    throw
                }}
                """
            for cmd in commands
        ))

        result = self._run_simple_command(script, timeout=timeout)
        if result.is_ok():
            output = result.unwrap()
            if isinstance(output, str):
                results: List[Any] = []
                current_result: List[str] = []
                in_result = False

                for line in output.splitlines():
                    if line.strip() == "COMMAND_RESULT_START":
                        in_result = True
                        current_result = []
                    elif line.strip() == "COMMAND_RESULT_END":
                        in_result = False
                        if current_result:
                            try:
                                json_result = json.loads('\n'.join(current_result))
                                results.append(json_result)
                            except json.JSONDecodeError:
                                results.append('\n'.join(current_result))
                    elif in_result:
                        current_result.append(line)

                return results
            else:
                return [output]
        else:
            error = result.unwrap_err()
            if isinstance(error, RetryableError):
                if "timed out" in str(error) or "Timeout" in str(error):
                    raise PowerShellTimeoutError(
                        f"Commands timed out after {timeout} seconds",
                        command=script
                    ) from error
                else:
                    raise PowerShellExecutionError(
                        str(error),
                        command=script,
                        stderr=error.stderr if hasattr(error, 'stderr') else str(error)
                    ) from error
            else:
                raise error

    def execute_script(self, script_content: str, timeout: int = 30) -> Any:
        """
        PowerShellスクリプトを実行
        
        Args:
            script_content: 実行するPowerShellスクリプトの内容
            timeout: タイムアウト時間（秒）
            
        Returns:
            Any: スクリプトの実行結果
            
        Raises:
            PowerShellExecutionError: スクリプト実行に失敗した場合
            PowerShellTimeoutError: タイムアウトした場合
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ps1', delete=False, encoding='utf-8') as f:
            f.write(script_content)
            script_path = f.name

        try:
            command = f". '{script_path}'"
            return self.execute_command(command, timeout)
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                self._log_event("script_cleanup_error", {"error": "Failed to delete temporary script file"}, "WARNING")

    def __del__(self) -> None:
        """デストラクタ：プロセスのクリーンアップを確実に行う"""
        if hasattr(self, 'process') and self.process:
            try:
                self.process.kill()
            except Exception:
                pass
