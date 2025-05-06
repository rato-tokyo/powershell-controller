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
import platform
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
from loguru import logger
from result import Result, Ok, Err

from py_pshell.core.session import PowerShellSession
from py_pshell.utils.config import PowerShellControllerSettings
from py_pshell.core.errors import (
    PowerShellError, 
    PowerShellExecutionError,
    PowerShellTimeoutError,
    CommunicationError,
    ProcessError,
    as_result
)
from py_pshell.session_manager import SessionManager
from py_pshell.command_executor import CommandExecutor


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

    def __init__(self, settings: Optional[PowerShellControllerSettings] = None):
        """
        SimplePowerShellControllerを初期化します。

        Args:
            settings: PowerShellControllerの設定。Noneの場合はデフォルト設定が使用されます。
        """
        self.settings = settings or PowerShellControllerSettings()
        self.logger = logger.bind(module="simple_controller")
        self._platform = platform.system().lower()
        
        # 依存コンポーネントの初期化
        self._session_manager = SessionManager(self.settings)
        self._command_executor = CommandExecutor(self._session_manager, self.settings)
        
        # 下位互換性のために保持
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
        """
        非同期でコントローラーのリソースを解放します。
        """
        # 既存のセッションを閉じる
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
        
        # SessionManagerを閉じる
        await self._session_manager.close()

    def close_sync(self) -> None:
        """
        同期的にコントローラーのリソースを解放します。
        
        注意: この実装はテスト中の警告を避けるために特殊な処理を含みます。
        """
        # テスト環境での警告を避けるために特殊なロジックを導入
        try:
            # 新しいループを作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # コルーチンをタスクに変換して実行（直接run_until_completeを使わない）
            # これによりテスト中の警告を軽減
            try:
                close_task = loop.create_task(self.close())
                loop.run_until_complete(close_task)
            finally:
                # 必ずループをクリーンアップ
                loop.close()
        except Exception:
            # 例外オブジェクト自体をキャプチャしない
            import traceback
            error_str = traceback.format_exc()
            self.logger.error(f"同期的クローズ処理でエラー発生:\n{error_str}")

    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """
        既存のイベントループを取得するか、新しいループを作成します。
        
        Returns:
            asyncio.AbstractEventLoop: イベントループ
        """
        try:
            # asyncio.get_event_loopは非推奨とされることがあるため、現在の推奨方法を使用
            try:
                # Python 3.7+
                return asyncio.get_running_loop()
            except AttributeError:
                # Python 3.6以前のために残す (get_running_loopがない場合)
                return asyncio.get_event_loop()
        except RuntimeError:
            # 'There is no current event loop in thread'
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def __del__(self) -> None:
        """
        オブジェクトが破棄される際にリソースを解放します。
        デストラクタでの非同期処理は避けるべきですが、リソースリークを防ぐため実装しています。
        """
        if not self._closed and hasattr(self, 'session') and self.session:
            # 警告回避のため、close_syncを直接呼び出すのではなく、
            # ここではログだけ出力してリソース解放を促す
            logger.warning(
                "SimplePowerShellControllerがデストラクタで解放されました。"
                "コンテキストマネージャまたはclose()メソッドを明示的に使用してリソースを適切に解放してください。"
            )
            # 可能な限り安全にセッションをマークする
            self._closed = True 