"""
シンプルなPowerShellコントローラー実装

このモジュールはPowerShellを操作するためのシンプルなインターフェースを提供します。
より高度な機能が必要ない場合は、このモジュールを使用することで、
コードの簡潔さと可読性を向上させることができます。
"""
from typing import Dict, Any, Optional, Union
from beartype.typing import List
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
from loguru import logger
from result import Result, Ok, Err

from powershell_controller.core.session import PowerShellSession
from powershell_controller.utils.config import PowerShellControllerSettings
from powershell_controller.core.errors import (
    PowerShellExecutionError,
    PowerShellTimeoutError,
    CommunicationError,
    ProcessError
)


class CommandResult(BaseModel):
    """コマンド実行結果を表すクラス"""
    output: str = ""
    error: Optional[str] = None
    success: bool = True
    details: Dict[str, Any] = {}

    def __str__(self) -> str:
        """文字列表現"""
        if self.success:
            return f"成功: {self.output}"
        else:
            return f"失敗: {self.error if self.error else '不明なエラー'}"

    def model_post_init(self, __context):
        """モデル初期化後の検証"""
        # successがFalseでerrorがNoneの場合は、デフォルトのエラーメッセージを設定
        if not self.success and self.error is None:
            self.error = "不明なエラーが発生しました"
            
        # successがTrueでerrorが設定されている場合は警告ログを出力
        if self.success and self.error:
            logger.warning(f"Command marked as successful but has error message: {self.error}")


class SimplePowerShellController:
    """
    シンプルなPowerShellコントローラー

    PowerShellの基本的な操作を簡単に行うためのインターフェースを提供します。
    """

    def __init__(self, settings: Optional[PowerShellControllerSettings] = None):
        """
        SimplePowerShellControllerを初期化します。

        Args:
            settings: PowerShellControllerの設定。Noneの場合はデフォルト設定が使用されます。
        """
        self.settings = settings or PowerShellControllerSettings()
        self.session: Optional[PowerShellSession] = None
        self._closed = False
        self._loop = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリーポイント"""
        if self._closed:
            raise RuntimeError("既に閉じられたコントローラーです")
        
        if not self.session:
            self.session = PowerShellSession(settings=self.settings)
            await self.session.__aenter__()
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了処理"""
        await self.close()

    async def run_command(self, command: str) -> CommandResult:
        """
        PowerShellコマンドを実行し、結果を返します。

        Args:
            command: 実行するPowerShellコマンド

        Returns:
            CommandResult: コマンドの実行結果
        """
        if self._closed:
            return CommandResult(
                output="",
                error="コントローラーは既に閉じられています",
                success=False,
                details={"error_type": "controller_closed"}
            )

        if not self.session:
            self.session = PowerShellSession(settings=self.settings)
            await self.session.__aenter__()

        try:
            output = await self.session.execute(command)
            return CommandResult(output=output, success=True, error=None)
        except PowerShellExecutionError as e:
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                details={"error_type": "execution_error", "command": command}
            )
        except PowerShellTimeoutError as e:
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                details={"error_type": "timeout_error", "command": command}
            )
        except CommunicationError as e:
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                details={"error_type": "communication_error", "command": command}
            )
        except ProcessError as e:
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                details={"error_type": "process_error", "command": command}
            )
        except Exception as e:
            return CommandResult(
                output="",
                error=f"予期しないエラー: {str(e)}",
                success=False,
                details={"error_type": "unexpected_error", "command": command}
            )

    async def run_commands(self, commands: List[str]) -> List[CommandResult]:
        """
        複数のPowerShellコマンドを順に実行し、結果のリストを返します。

        Args:
            commands: 実行するPowerShellコマンドのリスト

        Returns:
            List[CommandResult]: 各コマンドの実行結果のリスト
        """
        results = []
        for command in commands:
            result = await self.run_command(command)
            results.append(result)
            # エラーが発生した場合は残りのコマンドを実行しない
            if not result.success:
                break
        return results

    def _run_async_in_thread(self, coro):
        """非同期コルーチンをスレッドプールで実行する"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def execute_command_result(self, command: str) -> Result[str, Union[PowerShellExecutionError, PowerShellTimeoutError, Exception]]:
        """
        PowerShellコマンドを実行し、Result型で結果を返します。

        Args:
            command: 実行するPowerShellコマンド

        Returns:
            Result[str, Exception]: 成功した場合はOk(output)、失敗した場合はErr(exception)
        """
        async def _execute():
            if not self.session:
                self.session = PowerShellSession(settings=self.settings)
                await self.session.__aenter__()
                
            try:
                output = await self.session.execute(command)
                return Ok(output)
            except PowerShellExecutionError as e:
                return Err(e)
            except PowerShellTimeoutError as e:
                return Err(e)
            except Exception as e:
                return Err(e)

        # 非同期関数をスレッドプールで実行
        try:
            return self._executor.submit(self._run_async_in_thread, _execute()).result()
        except Exception as e:
            logger.error(f"コマンド実行中に予期しないエラーが発生: {e}")
            return Err(Exception(f"コマンド '{command}' の実行中にエラーが発生しました: {str(e)}"))

    def execute_commands_in_session_result(self, commands: List[str]) -> Result[List[str], Union[PowerShellExecutionError, PowerShellTimeoutError, Exception]]:
        """
        複数のPowerShellコマンドを同じセッションで実行し、Result型で結果を返します。

        Args:
            commands: 実行するPowerShellコマンドのリスト

        Returns:
            Result[List[str], Exception]: 成功した場合はOk(outputs)、失敗した場合はErr(exception)
        """
        async def _execute():
            if not self.session:
                self.session = PowerShellSession(settings=self.settings)
                await self.session.__aenter__()
                
            results = []
            for cmd in commands:
                try:
                    output = await self.session.execute(cmd)
                    results.append(output)
                except PowerShellExecutionError as e:
                    return Err(e)
                except PowerShellTimeoutError as e:
                    return Err(e)
                except Exception as e:
                    return Err(e)
            return Ok(results)

        # 非同期関数をスレッドプールで実行
        try:
            return self._executor.submit(self._run_async_in_thread, _execute()).result()
        except Exception as e:
            logger.error(f"複数コマンド実行中に予期しないエラーが発生: {e}")
            return Err(Exception(f"複数コマンドの実行中にエラーが発生しました: {str(e)}"))

    def execute_script_result(self, script: str) -> Result[str, Union[PowerShellExecutionError, PowerShellTimeoutError, Exception]]:
        """
        PowerShellスクリプトを実行し、Result型で結果を返します。

        Args:
            script: 実行するPowerShellスクリプト

        Returns:
            Result[str, Exception]: 成功した場合はOk(output)、失敗した場合はErr(exception)
        """
        return self.execute_command_result(script)

    async def close(self) -> None:
        """コントローラーを閉じ、関連するリソースを解放します"""
        if not self._closed and self.session:
            try:
                await self.session.__aexit__(None, None, None)
                await self.session.cleanup()
            except Exception as e:
                logger.error(f"セッションのクリーンアップ中にエラーが発生: {e}")
            finally:
                self.session = None
                self._closed = True
                self._executor.shutdown(wait=False) 