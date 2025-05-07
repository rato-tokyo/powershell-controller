"""
PowerShellコントローラーモジュール

PowerShellを制御するためのシンプルなインターフェースを提供します。
同期API（execute_command）と非同期API（run_command）の両方をサポートしています。
"""
import os
import sys
import asyncio
import platform
import threading
from typing import Dict, Any, Optional, List, Union
from loguru import logger
import time
from concurrent.futures import ThreadPoolExecutor

from .interfaces import CommandResultProtocol, PowerShellControllerProtocol
from .config import PowerShellControllerSettings
from .session import PowerShellSession
from .utils.command_result import CommandResult
from .errors import (
    PowerShellError,
    PowerShellExecutionError,
    PowerShellTimeoutError,
    PowerShellStartupError,
    PowerShellShutdownError
)

class PowerShellController(PowerShellControllerProtocol):
    """
    PowerShellコントローラー
    
    PowerShellコマンドを実行するためのシンプルなインターフェースを提供します。
    同期APIと非同期API、およびResult型を使用したエラーハンドリングをサポートします。
    
    使用例:
        # 同期API
        controller = PowerShellController()
        try:
            output = controller.execute_command("Get-Process")
            print(output)
        finally:
            controller.close_sync()
            
        # 非同期API
        async with PowerShellController() as controller:
            result = await controller.run_command("Get-Process")
            if result.success:
                print(result.output)
                
        # try-exceptによるエラーハンドリング
        try:
            output = controller.execute_command("Get-Process")
            print(output)
        except PowerShellExecutionError as e:
            print(f"エラー: {e}")
    """
    
    def __init__(self, settings: Optional[PowerShellControllerSettings] = None):
        """
        PowerShellコントローラーを初期化します。
        
        Args:
            settings: コントローラーの設定。Noneの場合はデフォルト設定が使用されます。
        """
        self.settings = settings or PowerShellControllerSettings()
        self.session: Optional[PowerShellSession] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = threading.RLock()
        logger.debug("PowerShellControllerが初期化されました")
    
    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリーポイント"""
        if not self.session:
            self.session = PowerShellSession(settings=self.settings)
            await self.session.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了処理"""
        await self.close()
    
    async def close(self) -> None:
        """
        PowerShellセッションを閉じます。
        """
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
            logger.debug("PowerShellSessionが閉じられました")
            
    def close_sync(self) -> None:
        """
        PowerShellセッションを同期的に閉じます。
        """
        if self.session:
            loop = self._get_or_create_loop()
            coro = self.close()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            try:
                future.result(timeout=self.settings.timeout.shutdown)
            except Exception as e:
                logger.error(f"セッションのクローズに失敗: {e}")
                # 強制終了処理は何もしない（既に実施済み）
    
    async def run_command(self, command: str, timeout: Optional[float] = None) -> CommandResult:
        """
        PowerShellコマンドを実行します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            CommandResult: コマンドの実行結果
        """
        if not self.session:
            self.session = PowerShellSession(settings=self.settings)
            await self.session.__aenter__()
        
        start_time = time.time()
        try:
            output = await self.session.execute(command, timeout)
            elapsed = time.time() - start_time
            
            return CommandResult(
                output=output,
                error="",
                success=True,
                command=command,
                execution_time=elapsed
            )
        except PowerShellError as e:
            elapsed = time.time() - start_time
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                command=command,
                execution_time=elapsed
            )
    
    async def run_script(self, script: str, timeout: Optional[float] = None) -> CommandResult:
        """
        PowerShellスクリプトを実行します。
        
        Args:
            script: 実行するPowerShellスクリプト
            timeout: スクリプト実行のタイムアウト（秒）
            
        Returns:
            CommandResult: スクリプトの実行結果
        """
        # スクリプトの実行はコマンドの実行と同じ
        return await self.run_command(script, timeout)
    
    def execute_command(self, command: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellコマンドを同期的に実行します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            str: コマンドの実行結果
            
        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
        """
        loop = self._get_or_create_loop()
        coro = self.run_command(command, timeout)
        
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        try:
            result = future.result(timeout=timeout or self.settings.timeout.default)
            
            if not result.success:
                raise PowerShellExecutionError(result.error, command)
                
            return result.output
        except Exception as e:
            if isinstance(e, PowerShellError):
                raise
            else:
                raise PowerShellError(f"コマンド実行中にエラーが発生しました: {e}", command)
    
    def execute_script(self, script: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellスクリプトを実行します。
        
        Args:
            script: 実行するPowerShellスクリプト
            timeout: スクリプト実行のタイムアウト（秒）
            
        Returns:
            str: スクリプトの実行結果
            
        Raises:
            PowerShellExecutionError: スクリプトの実行に失敗した場合
        """
        # スクリプトの実行はコマンドの実行と同じ
        return self.execute_command(script, timeout)
    
    def get_json(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        PowerShellコマンドを実行し、結果をJSON形式で解析して返します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            Dict[str, Any]: JSONデータを解析した辞書
            
        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
            ValueError: JSONの解析に失敗した場合
        """
        import json
        
        # ConvertTo-Jsonが含まれていない場合は追加する
        if "ConvertTo-Json" not in command:
            command = f"{command} | ConvertTo-Json -Depth 10"
            
        output = self.execute_command(command, timeout)
        
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSONの解析に失敗しました: {e}\n元データ: {output}")
    
    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """
        イベントループを取得または作成します。
        
        Returns:
            asyncio.AbstractEventLoop: イベントループ
        """
        with self._lock:
            if self._loop is None or self._loop.is_closed():
                # 新しいループを作成
                if hasattr(asyncio, "get_running_loop"):
                    try:
                        self._loop = asyncio.get_running_loop()
                    except RuntimeError:
                        # 実行中のループがない場合は新しいループを作成
                        self._loop = asyncio.new_event_loop()
                else:
                    # Python 3.6
                    try:
                        self._loop = asyncio.get_event_loop()
                    except RuntimeError:
                        self._loop = asyncio.new_event_loop()
                
                # ループがスレッドで実行されていることを確認
                if not self._loop.is_running():
                    # ループはまだ実行されていないため、バックグラウンドスレッドで実行
                    thread = threading.Thread(
                        target=self._run_event_loop, 
                        args=(self._loop,),
                        daemon=True
                    )
                    thread.start()
                
            return self._loop
    
    def _run_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        イベントループをバックグラウンドスレッドで実行します。
        
        Args:
            loop: 実行するイベントループ
        """
        asyncio.set_event_loop(loop)
        loop.run_forever()
        
    def __del__(self) -> None:
        """デストラクタ"""
        try:
            # スレッドプールを終了
            if hasattr(self, "_executor"):
                self._executor.shutdown(wait=False)
            
            # セッションがあればクローズ
            if hasattr(self, "session") and self.session:
                loop = None
                try:
                    if hasattr(self, "_loop") and self._loop and not self._loop.is_closed():
                        loop = self._loop
                except:
                    pass
                
                if loop:
                    try:
                        future = asyncio.run_coroutine_threadsafe(self.close(), loop)
                        future.result(timeout=1.0)
                    except:
                        pass
        except:
            # デストラクタでの例外は無視
            pass 