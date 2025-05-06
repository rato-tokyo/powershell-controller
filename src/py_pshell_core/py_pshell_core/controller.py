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

# py_pshell_utilsパッケージからのインポート
from py_pshell_utils.config import PowerShellControllerSettings
from py_pshell_utils.errors import (
    PowerShellError, 
    PowerShellExecutionError,
    PowerShellTimeoutError,
    CommunicationError,
    ProcessError,
    as_result
)

# 将来的には内部モジュールをインポートする
# ここではモックとして定義
class PowerShellSession:
    """
    PowerShellセッションのモッククラス
    後で実装に置き換える
    """
    def __init__(self, settings=None):
        self.settings = settings
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def execute(self, command):
        return f"モック出力: {command}"

# 一時的なモッククラス
class SessionManager:
    def __init__(self, settings=None):
        self.settings = settings
        
class CommandExecutor:
    def __init__(self, session_manager, settings=None):
        self.session_manager = session_manager
        self.settings = settings
        
    def execute_sync(self, command):
        return f"モック出力: {command}"

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
                error=str(e),
                success=False,
                details={"error_type": "unknown_error", "command": command}
            )

    async def run_commands(self, commands: List[str]) -> List[CommandResult]:
        """
        複数のPowerShellコマンドを連続して実行します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            各コマンドの実行結果のリスト
        """
        results = []
        for cmd in commands:
            result = await self.run_command(cmd)
            results.append(result)
            if not result.success:
                break
        return results

    def _run_async_in_thread(self, coro):
        """
        非同期関数をスレッドで実行します。
        
        Args:
            coro: 実行する非同期コルーチン
            
        Returns:
            コルーチンの結果
        """
        loop = self._get_or_create_loop()
        return asyncio.run_coroutine_threadsafe(coro, loop).result()

    def execute_command_result(self, command: str) -> Result[str, Union[PowerShellExecutionError, PowerShellTimeoutError, Exception]]:
        """
        単一のPowerShellコマンドを実行し、Result型で結果を返します。
        
        Args:
            command: 実行するコマンド
            
        Returns:
            Result型の結果
        """
        try:
            output = self.execute_command_sync(command)
            return Ok(output)
        except PowerShellExecutionError as e:
            self.logger.error(f"コマンド実行エラー: {e}")
            return Err(e)
        except PowerShellTimeoutError as e:
            self.logger.error(f"コマンド実行タイムアウト: {e}")
            return Err(e)
        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}")
            if isinstance(e, PowerShellError):
                return Err(e)
            else:
                return Err(PowerShellExecutionError(f"コマンド実行エラー: {e}"))

    def execute_commands_in_session(self, commands: List[str]) -> List[Any]:
        """
        単一のセッションで複数のコマンドを実行します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            各コマンドの実行結果のリスト
        """
        results = []
        for cmd in commands:
            output = self.execute_command(cmd)
            results.append(output)
        return results

    @as_result
    def execute_commands_in_session_result(self, commands: List[str]) -> Result[List[str], PowerShellError]:
        """
        単一のセッションで複数のコマンドを実行し、Result型で結果を返します。
        
        Args:
            commands: 実行するコマンドのリスト
            
        Returns:
            Result型の結果
        """
        results = []
        for cmd in commands:
            output = self.execute_command(cmd)
            results.append(output)
        return results

    def execute_script(self, script: str) -> str:
        """
        PowerShellスクリプトを実行します。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            スクリプトの実行結果
        """
        self.logger.debug(f"スクリプトを実行します: {script[:50]}...")
        return self.execute_command(script)

    def execute_script_result(self, script: str) -> Result[str, Union[PowerShellExecutionError, PowerShellTimeoutError, Exception]]:
        """
        PowerShellスクリプトを実行し、Result型で結果を返します。
        
        Args:
            script: 実行するスクリプト
            
        Returns:
            Result型の結果
        """
        return self.execute_command_result(script)

    async def close(self) -> None:
        """
        コントローラーを閉じます。
        """
        if self._closed:
            return

        self.logger.debug("コントローラーを閉じています...")
        self._closed = True

        # セッションを閉じる
        if self.session:
            try:
                await self.session.__aexit__(None, None, None)
                self.session = None
            except Exception as e:
                self.logger.error(f"セッションを閉じる際にエラーが発生しました: {e}")

        # ExecutorPoolを閉じる
        try:
            self._executor.shutdown(wait=False)
        except Exception as e:
            self.logger.error(f"ThreadPoolExecutorの終了中にエラーが発生しました: {e}")

    def close_sync(self) -> None:
        """
        コントローラーを同期的に閉じます。
        """
        if self._closed:
            return
            
        self.logger.debug("コントローラーを同期的に閉じています...")
        self._closed = True
        
        # セッションを閉じる（簡易実装）
        if self.session and self._loop and self._loop.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(self.session.__aexit__(None, None, None), self._loop)
                future.result(timeout=5.0)
                self.session = None
            except Exception as e:
                self.logger.error(f"セッションを同期的に閉じる際にエラーが発生しました: {e}")
        
        # ExecutorPoolを閉じる
        try:
            self._executor.shutdown(wait=False)
        except Exception as e:
            self.logger.error(f"ThreadPoolExecutorの終了中にエラーが発生しました: {e}")

    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """
        既存のループを取得するか、新しいループを作成します。
        
        Returns:
            イベントループ
        """
        # 既存のループがある場合はそれを返す
        if self._loop and self._loop.is_running():
            return self._loop
            
        # 現在のスレッドにループがあるか確認
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_closed():
                self._loop = loop
                return loop
        except RuntimeError:
            # 現在のスレッドにループがない場合は新しく作成
            pass
            
        # 新しいループを作成して設定
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        
        # ループを別スレッドで実行
        def run_event_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
            
        threading.Thread(target=run_event_loop, args=(loop,), daemon=True).start()
        return loop

    def __del__(self) -> None:
        """
        デストラクタ
        オブジェクトが破棄される前にリソースを解放します。
        """
        if not self._closed:
            # 同期的に閉じる
            try:
                self.close_sync()
            except Exception as e:
                # デストラクタでは例外を投げてはいけない
                pass
                
__all__ = [
    'SimplePowerShellController',
    'CommandResult'
] 