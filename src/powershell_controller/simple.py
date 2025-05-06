"""
シンプルなPowerShellコントローラーの実装
"""
from typing import Any, List, Optional, Union, Dict, Callable, Awaitable, TypeVar, cast
import asyncio
from loguru import logger
from result import Result, Ok, Err

from .core.session import PowerShellSession
from .core.errors import PowerShellError, PowerShellExecutionError
from .utils.result_helper import ResultHandler

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
    
    def __init__(self) -> None:
        """コントローラーを初期化します。"""
        self.logger = logger.bind(module="simple_controller")
        
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
            raise PowerShellExecutionError(f"コマンド実行エラー: {e}")
            
    def execute_command_result(self, command: str) -> Result[Any, PowerShellError]:
        """
        単一のPowerShellコマンドを実行し、Result型で結果を返します。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            Result型の実行結果
        """
        return ResultHandler.from_function(self.execute_command_sync, command)
        
    def execute_command_sync(self, command: str) -> Any:
        """
        同期的にPowerShellコマンドを実行します。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            コマンドの実行結果
            
        Raises:
            PowerShellExecutionError: コマンド実行時にエラーが発生した場合
        """
        session = PowerShellSession()
        
        try:
            # 非同期メソッドを同期的に実行するためのヘルパー関数
            async def _execute_async() -> Any:
                async with session:
                    return await session.execute(command)
                    
            # 実行してループが終了するまで待機
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(_execute_async())
            return result
        except Exception as e:
            self.logger.error(f"コマンド '{command}' の実行中にエラーが発生しました: {e}")
            raise PowerShellExecutionError(f"コマンド実行エラー: {e}")
        finally:
            # セッションのクリーンアップ
            loop = asyncio.get_event_loop()
            loop.run_until_complete(session.cleanup())
            
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
        async def _run_commands() -> List[Any]:
            results: List[Any] = []
            session = PowerShellSession()
            
            try:
                async with session:
                    for command in commands:
                        result = await session.execute(command)
                        results.append(result)
                return results
            except Exception as e:
                self.logger.error(f"コマンド実行中にエラーが発生しました: {e}")
                raise PowerShellExecutionError(f"コマンド実行エラー: {e}")
                
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_run_commands())
        finally:
            loop.close()
            
    def execute_commands_in_session_result(self, commands: List[str]) -> Result[List[Any], PowerShellError]:
        """
        複数のPowerShellコマンドを単一セッションで実行し、Result型で結果を返します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            Result型の実行結果のリスト
        """
        return ResultHandler.from_function(self.execute_commands_in_session, commands)
        
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
        
    def execute_script_result(self, script: str) -> Result[str, PowerShellError]:
        """
        PowerShellスクリプトを実行し、Result型で結果を返します。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            Result型の実行結果
        """
        return ResultHandler.from_function(self.execute_script, script) 