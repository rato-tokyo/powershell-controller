"""
PowerShellコマンド実行を担当するモジュール

このモジュールはPowerShellコマンド実行に特化したクラスを提供します。
"""
from typing import Any, List, Optional, Dict, TypeVar, cast
import asyncio
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from tenacity import retry_if_exception_type
from result import Result, Ok, Err

from .core.errors import (
    PowerShellError, 
    PowerShellExecutionError, 
    PowerShellTimeoutError,
    ProcessError,
    CommunicationError,
    as_result
)
from .utils.config import PowerShellControllerSettings
from .session_manager import SessionManager

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


class CommandExecutor:
    """
    PowerShellコマンド実行を担当するクラス
    
    このクラスはPowerShellコマンドとスクリプトの実行ロジックを提供します。
    """
    
    def __init__(self, session_manager: SessionManager, settings: PowerShellControllerSettings):
        """
        コマンド実行クラスを初期化します。
        
        Args:
            session_manager: PowerShellセッションを管理するマネージャー
            settings: PowerShell設定
        """
        self.settings = settings
        self._session_manager = session_manager
        self.logger = logger.bind(module="command_executor")
        
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
            session = await self._session_manager.get_session()
                
            start_time = asyncio.get_event_loop().time()
            output = await session.execute(command)
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
            # セッションをリセット
            await self._session_manager.reset_session()
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

    def execute_sync(self, command: str) -> str:
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
            # コマンド実行
            result = loop.run_until_complete(self.run_command(command))
            
            # 実行結果の確認
            if not result.success:
                raise PowerShellExecutionError(
                    f"コマンド '{command}' の実行に失敗しました: {result.error}",
                    details=str(result.details) if result.details else None
                )
                
            return result.output
            
        except PowerShellError:
            # PowerShellErrorはそのまま再スロー
            raise
        except Exception as e:
            # その他の例外はPowerShellExecutionErrorに変換
            raise PowerShellExecutionError(f"コマンド '{command}' の実行中にエラーが発生しました: {e}")

    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """
        既存のイベントループを取得するか、新しいループを作成します。
        
        Returns:
            asyncio.AbstractEventLoop: イベントループ
        """
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            # 'There is no current event loop in thread'
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def execute_commands_in_session(self, commands: List[str]) -> List[Any]:
        """
        複数のコマンドを同一セッションで連続実行します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            List[Any]: 各コマンドの実行結果のリスト
        """
        loop = self._get_or_create_loop()
        
        # 連続実行用の非同期関数
        async def _run_commands_in_session():
            results = []
            session = await self._session_manager.get_session()
            
            for cmd in commands:
                try:
                    output = await session.execute(cmd)
                    results.append(output)
                except Exception as e:
                    # エラーが発生した場合は中断
                    self.logger.error(f"コマンド '{cmd}' の実行中にエラーが発生: {e}")
                    raise
            
            return results
        
        # 実行
        try:
            return loop.run_until_complete(_run_commands_in_session())
        except PowerShellError:
            # PowerShellErrorはそのまま再スロー
            raise
        except Exception as e:
            # その他の例外はPowerShellExecutionErrorに変換
            raise PowerShellExecutionError(f"複数コマンドの実行中にエラーが発生しました: {e}")

    @as_result
    def execute_commands_in_session_result(self, commands: List[str]) -> Result[List[str], PowerShellError]:
        """
        複数のコマンドを同一セッションで連続実行し、Result型で結果を返します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            Result[List[str], PowerShellError]: 成功の場合はOk(出力のリスト)、失敗の場合はErr(エラー)
        """
        try:
            results = self.execute_commands_in_session(commands)
            return Ok(results)
        except PowerShellError as e:
            self.logger.error(f"複数コマンド実行エラー: {e}")
            return Err(e)
        except Exception as e:
            error = PowerShellExecutionError(f"複数コマンド実行エラー: {e}")
            self.logger.error(f"予期しないエラー (複数コマンド): {e}")
            return Err(error)

    def execute_script(self, script: str) -> str:
        """
        PowerShellスクリプトを実行します。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            str: スクリプトの実行結果
        """
        # スクリプトの実行は単一コマンドの実行と同じ
        return self.execute_sync(script)

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
            self.logger.error(f"スクリプト実行エラー: {e}")
            return Err(e)
        except Exception as e:
            error = PowerShellExecutionError(f"スクリプト実行エラー: {e}")
            self.logger.error(f"予期しないエラー (スクリプト): {e}")
            return Err(error) 