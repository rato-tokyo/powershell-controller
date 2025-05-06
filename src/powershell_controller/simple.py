"""
シンプルなPowerShellコントローラーの実装
"""
from typing import Any, List, Optional, Union, Dict, Callable, Awaitable, TypeVar, cast
import asyncio
import platform
import sys
from loguru import logger
from result import Result, Ok, Err
from pydantic import BaseModel, Field, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from tenacity import retry_if_exception_type

from .core.session import PowerShellSession
from .core.errors import (
    PowerShellError, 
    PowerShellExecutionError, 
    PowerShellTimeoutError, 
    as_result,
    CommunicationError,
    ProcessError
)
from .utils.result_helper import ResultHandler
from .utils.config import PowerShellControllerSettings

T = TypeVar('T')

class CommandResult(BaseModel):
    """
    コマンド実行結果を表すクラス
    
    Attributes:
        output: コマンド実行の標準出力
        error: エラーメッセージ（存在する場合）
        success: コマンドが成功したかどうか
        details: 追加のエラー詳細情報
    """
    output: str = Field(default="", description="コマンド実行の標準出力")
    error: Optional[str] = Field(default=None, description="エラーメッセージ（存在する場合）")
    success: bool = Field(default=True, description="コマンドが成功したかどうか")
    details: Optional[Dict[str, Any]] = Field(default=None, description="追加のエラー詳細情報")
    
    @field_validator('success')
    def validate_success_and_error(cls, v, info):
        """successとerrorの整合性を検証する"""
        values = info.data
        if not v and not values.get('error'):
            # 失敗しているのにエラーメッセージがない場合は、デフォルトメッセージを設定
            values['error'] = "Unknown error occurred"
        elif v and values.get('error'):
            # 成功しているのにエラーメッセージがある場合は警告ログを出力
            logger.warning(f"Command marked as successful but has error message: {values.get('error')}")
        return v

class SimplePowerShellController:
    """
    シンプルなPowerShellコントローラー
    
    Example:
        ```python
        controller = SimplePowerShellController()
        result = controller.execute_command("Write-Output 'Hello, World!'")
        print(result)  # "Hello, World!"
        
        # Result型を使用した例
        result = controller.execute_command_result("Get-Process")
        if result.is_ok():
            processes = result.unwrap()
            print(f"プロセス数: {len(processes)}")
        else:
            error = result.unwrap_err()
            print(f"エラーが発生しました: {error}")
        ```
    """
    
    def __init__(self, settings: Optional[PowerShellControllerSettings] = None) -> None:
        """
        コントローラーを初期化します。
        
        Args:
            settings: PowerShellコントローラーの設定。Noneの場合はデフォルト設定を使用。
        """
        self.settings = settings or PowerShellControllerSettings()
        self.logger = logger.bind(module="simple_controller")
        self._session: Optional[PowerShellSession] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._platform = platform.system().lower()
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=10),
        retry=retry_if_exception_type((PowerShellExecutionError, ConnectionError, CommunicationError)),
        before_sleep=lambda retry_state: logger.info(
            f"リトライ実行 {retry_state.attempt_number}/3 - "
            f"前回エラー: {retry_state.outcome.exception()}"
        )
    )
    async def run_command(self, command: str) -> CommandResult:
        """
        単一のPowerShellコマンドを非同期で実行します。リトライロジック付き。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            CommandResult: コマンドの実行結果を含むオブジェクト
        """
        self.logger.info(f"コマンド実行開始", command=command)
        
        try:
            if self._session is None:
                self.logger.debug("新しいセッションを作成")
                self._session = PowerShellSession(settings=self.settings)
                await self._session.__aenter__()
                
            start_time = asyncio.get_event_loop().time()
            output = await self._session.execute(command)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            self.logger.info(
                f"コマンド実行成功", 
                command=command, 
                elapsed_ms=int(elapsed * 1000),
                output_length=len(output)
            )
            
            return CommandResult(output=output, success=True)
            
        except PowerShellExecutionError as e:
            self.logger.error(
                f"コマンド実行エラー", 
                command=command,
                error=str(e),
                error_type="execution_error"
            )
            details = {"error_type": "execution_error", "command": command}
            if hasattr(e, "details"):
                details["additional_info"] = e.details
            return CommandResult(output="", error=str(e), success=False, details=details)
            
        except PowerShellTimeoutError as e:
            self.logger.error(
                f"コマンド実行タイムアウト", 
                command=command,
                error=str(e),
                error_type="timeout_error"
            )
            details = {"error_type": "timeout_error", "command": command}
            return CommandResult(output="", error=f"タイムアウトエラー: {e}", success=False, details=details)
            
        except ProcessError as e:
            self.logger.error(
                f"プロセスエラー", 
                command=command,
                error=str(e),
                error_type="process_error"
            )
            # 自動的にセッションをリセット
            await self._reset_session()
            details = {"error_type": "process_error", "command": command}
            return CommandResult(output="", error=f"プロセスエラー: {e}", success=False, details=details)
            
        except Exception as e:
            self.logger.error(
                f"予期しないエラー", 
                command=command,
                error=str(e),
                error_type=type(e).__name__
            )
            details = {"error_type": type(e).__name__, "command": command}
            return CommandResult(output="", error=f"エラー: {e}", success=False, details=details)
    
    async def _reset_session(self) -> None:
        """
        エラー発生時にセッションをリセットします
        """
        self.logger.warning("セッションをリセットします")
        if self._session:
            try:
                await self._session.cleanup()
            except Exception as e:
                self.logger.error(f"セッションクリーンアップ中にエラーが発生: {e}")
            finally:
                self._session = None
        
    def execute_command(self, command: str) -> Any:
        """
        単一のPowerShellコマンドを実行します。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            コマンドの実行結果
            
        Raises:
            PowerShellExecutionError: コマンド実行時にエラーが発生した場合
        """
        try:
            return self.execute_command_sync(command)
        except Exception as e:
            self.logger.error(f"コマンド '{command}' の実行中にエラーが発生しました: {e}")
            if isinstance(e, PowerShellError):
                raise
            else:
                raise PowerShellExecutionError(f"コマンド実行エラー: {e}")
    
    @as_result
    def execute_command_result(self, command: str) -> Result[str, PowerShellError]:
        """
        単一のPowerShellコマンドを実行し、Result型で結果を返します。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            Result[str, PowerShellError]: 成功の場合はOk(出力)、失敗の場合はErr(エラー)
        """
        try:
            result = self.execute_command_sync(command)
            return Ok(result)
        except PowerShellError as e:
            self.logger.error(
                f"コマンド実行エラー (Result)", 
                command=command,
                error=str(e),
                error_type=type(e).__name__
            )
            return Err(e)
        except Exception as e:
            self.logger.error(
                f"予期しないエラー (Result)", 
                command=command,
                error=str(e),
                error_type=type(e).__name__
            )
            error = PowerShellExecutionError(f"コマンド実行エラー: {e}")
            return Err(error)

    def execute_command_sync(self, command: str) -> str:
        """
        単一のPowerShellコマンドを同期的に実行します。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            str: コマンドの実行結果
            
        Raises:
            PowerShellExecutionError: コマンド実行時にエラーが発生した場合
        """
        loop = self._get_or_create_loop()
        
        try:
            # PowerShellセッションを取得または作成
            session = loop.run_until_complete(self._get_or_create_session(loop))
            
            # コマンド実行
            self.logger.debug(f"コマンド実行（同期）: {command}")
            result = loop.run_until_complete(session.execute(command))
            
            return result
        except Exception as e:
            self.logger.error(f"コマンド実行エラー (同期): {e}")
            if isinstance(e, PowerShellError):
                raise
            else:
                raise PowerShellExecutionError(f"コマンド実行エラー: {e}")
            
    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """
        イベントループを取得または作成します。
        
        Returns:
            イベントループ
        """
        if self._loop is None or self._loop.is_closed():
            try:
                # 既存のイベントループを取得
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                # イベントループがない場合は新しく作成
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        
        return self._loop
    
    def _get_or_create_session(self, loop: asyncio.AbstractEventLoop) -> PowerShellSession:
        """
        PowerShellセッションを取得または作成します。
        
        Args:
            loop: イベントループ
            
        Returns:
            PowerShellセッション
        """
        if self._session is None:
            # 新しいセッションを作成して初期化
            self._session = PowerShellSession(settings=self.settings)
            loop.run_until_complete(self._session.__aenter__())
        
        return self._session
            
    def execute_commands_in_session(self, commands: List[str]) -> List[Any]:
        """
        複数のPowerShellコマンドを単一セッションで実行します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            各コマンドの実行結果のリスト
            
        Raises:
            PowerShellExecutionError: コマンド実行時にエラーが発生した場合
        """
        if not commands:
            return []
            
        try:
            # イベントループとセッションを初期化
            loop = self._get_or_create_loop()
            session = self._get_or_create_session(loop)
            
            # 複数コマンドを順番に実行
            results = []
            for command in commands:
                self.logger.debug(f"Executing command in session: {command}")
                result = loop.run_until_complete(session.execute(command))
                
                # Resultを返すのでunwrapして実際の結果を取り出す
                if hasattr(result, 'is_ok') and callable(getattr(result, 'is_ok')):
                    if result.is_ok():
                        results.append(result.unwrap())
                    else:
                        error = result.unwrap_err()
                        raise error
                else:
                    results.append(result)
            
            return results
            
        except PowerShellError as e:
            self.logger.error(f"PowerShellエラー: {e}")
            raise
        except Exception as e:
            self.logger.error(f"複数コマンド実行中にエラーが発生しました: {e}")
            raise PowerShellExecutionError(f"複数コマンド実行エラー: {e}")
    
    @as_result
    def execute_commands_in_session_result(self, commands: List[str]) -> Result[List[str], PowerShellError]:
        """
        複数のPowerShellコマンドを同じセッションで実行し、Result型で結果を返します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            Result[List[str], PowerShellError]: 成功の場合はOk(出力のリスト)、失敗の場合はErr(エラー)
        """
        try:
            results = self.execute_commands_in_session(commands)
            return Ok(results)
        except PowerShellError as e:
            self.logger.error(
                f"コマンドシーケンス実行エラー (Result)", 
                commands_count=len(commands),
                error=str(e),
                error_type=type(e).__name__
            )
            return Err(e)
        except Exception as e:
            self.logger.error(
                f"予期しないエラー (Result)", 
                commands_count=len(commands),
                error=str(e),
                error_type=type(e).__name__
            )
            error = PowerShellExecutionError(f"コマンド実行エラー: {e}")
            return Err(error)
        
    def execute_script(self, script: str) -> str:
        """
        PowerShellスクリプトを実行します。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            スクリプトの実行結果
            
        Raises:
            PowerShellExecutionError: スクリプト実行時にエラーが発生した場合
        """
        # スクリプトを一時ファイルに保存してパラメータとして渡す方法
        temp_script = f"""
        $tempScriptBlock = {{
{script}
        }}
        
        # スクリプトブロックを実行して結果を返す
        & $tempScriptBlock
        """
        
        result = self.execute_command(temp_script)
        return cast(str, result)
    
    @as_result
    def execute_script_result(self, script: str) -> Result[str, PowerShellError]:
        """
        PowerShellスクリプトを実行し、Result型で結果を返します。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            Result[str, PowerShellError]: 成功の場合はOk(出力)、失敗の場合はErr(エラー)
        """
        try:
            result = self.execute_script(script)
            return Ok(result)
        except PowerShellError as e:
            self.logger.error(
                f"スクリプト実行エラー (Result)", 
                script_length=len(script),
                error=str(e),
                error_type=type(e).__name__
            )
            return Err(e)
        except Exception as e:
            self.logger.error(
                f"予期しないエラー (Result)", 
                script_length=len(script),
                error=str(e),
                error_type=type(e).__name__
            )
            error = PowerShellExecutionError(f"スクリプト実行エラー: {e}")
            return Err(error)
    
    async def close(self) -> None:
        """
        コントローラーをクリーンアップします。すべてのPowerShellセッションを閉じます。
        """
        try:
            if self._session:
                self.logger.debug("PowerShellセッションを終了しています...")
                await self._session.__aexit__(None, None, None)
                self._session = None
                self.logger.debug("PowerShellセッションを終了しました")
        except Exception as e:
            self.logger.error(f"セッションクローズエラー: {e}")
        finally:
            # エラーが発生してもセッション参照をクリア
            self._session = None

    def close_sync(self) -> None:
        """
        コントローラーを同期的にクリーンアップします。
        """
        if self._session:
            loop = self._get_or_create_loop()
            try:
                self.logger.debug("PowerShellセッションを終了しています（同期）...")
                loop.run_until_complete(self.close())
                self.logger.debug("PowerShellセッションを終了しました（同期）")
            except Exception as e:
                self.logger.error(f"セッションクローズエラー（同期）: {e}")
            finally:
                # エラーが発生してもセッション参照をクリア
                self._session = None
    
    def __del__(self) -> None:
        """
        インスタンスが破棄されるときにリソースを解放します。
        """
        if self._loop and not self._loop.is_closed():
            self.close_sync() 