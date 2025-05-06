"""
PowerShellコントローラーのメインクラス

このモジュールはPowerShellコマンドの実行を管理する主要なコントローラークラスを提供します。
"""
from typing import Any, List, Optional, Union, Dict, TypeVar
import asyncio
import platform
from loguru import logger
from result import Result, Ok, Err

from .core.session import PowerShellSession
from .core.errors import (
    PowerShellError, 
    PowerShellExecutionError, 
    as_result
)
from .utils.result_helper import ResultHandler
from .utils.config import PowerShellControllerSettings
from .command_executor import CommandExecutor, CommandResult
from .session_manager import SessionManager

T = TypeVar('T')

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
        self._platform = platform.system().lower()
        
        # 依存コンポーネントの初期化
        self._session_manager = SessionManager(self.settings)
        self._command_executor = CommandExecutor(self._session_manager, self.settings)
    
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
        return self._command_executor.execute_sync(command)

    def execute_commands_in_session(self, commands: List[str]) -> List[Any]:
        """
        複数のコマンドを同一セッションで連続実行します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            List[Any]: 各コマンドの実行結果のリスト
        """
        return self._command_executor.execute_commands_in_session(commands)

    @as_result
    def execute_commands_in_session_result(self, commands: List[str]) -> Result[List[str], PowerShellError]:
        """
        複数のコマンドを同一セッションで連続実行し、Result型で結果を返します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            Result[List[str], PowerShellError]: 成功の場合はOk(出力のリスト)、失敗の場合はErr(エラー)
        """
        return self._command_executor.execute_commands_in_session_result(commands)

    def execute_script(self, script: str) -> str:
        """
        PowerShellスクリプトを実行します。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            str: スクリプトの実行結果
        """
        return self._command_executor.execute_script(script)

    @as_result
    def execute_script_result(self, script: str) -> Result[str, PowerShellError]:
        """
        PowerShellスクリプトを実行し、Result型で結果を返します。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            Result[str, PowerShellError]: 成功の場合はOk(出力)、失敗の場合はErr(エラー)
        """
        return self._command_executor.execute_script_result(script)

    async def close(self) -> None:
        """
        非同期でコントローラーのリソースを解放します。
        """
        await self._session_manager.close()

    def close_sync(self) -> None:
        """
        同期的にコントローラーのリソースを解放します。
        """
        loop = self._get_or_create_loop()
        try:
            loop.run_until_complete(self.close())
        except RuntimeError:
            # ループが既に実行中の場合
            asyncio.create_task(self.close())

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

    def __del__(self) -> None:
        """
        オブジェクトが破棄される際にリソースを解放します。
        """
        try:
            self.close_sync()
        except Exception as e:
            # デストラクタ内でのエラーはログに記録するだけ
            self.logger.error(f"デストラクタでのクリーンアップ中にエラーが発生: {e}") 