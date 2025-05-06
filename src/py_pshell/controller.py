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
from pydantic import BaseModel, Field
from loguru import logger
from result import Result, Ok, Err
import time
from concurrent.futures import ThreadPoolExecutor

from .interfaces import CommandResultProtocol, PowerShellControllerProtocol
from .config import PowerShellControllerSettings
from .session import PowerShellSession
from .errors import (
    PowerShellError,
    PowerShellExecutionError,
    PowerShellTimeoutError,
    PowerShellStartupError,
    PowerShellShutdownError,
    as_result
)

class CommandResult(BaseModel, CommandResultProtocol):
    """
    PowerShellコマンドの実行結果
    
    Attributes:
        output: コマンドの標準出力
        error: コマンドの標準エラー出力
        success: コマンドが成功したかどうか
        command: 実行されたコマンド
        execution_time: 実行時間（秒）
    """
    output: str = ""
    error: str = ""
    success: bool = True
    command: str = ""
    execution_time: float = 0.0
    
    def __str__(self) -> str:
        """文字列表現を返します"""
        if self.success:
            return self.output
        return f"エラー: {self.error}"
    
    def __bool__(self) -> bool:
        """ブール値変換（成功したかどうか）"""
        return self.success
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で結果を返します"""
        return {
            "output": self.output,
            "error": self.error,
            "success": self.success,
            "command": self.command,
            "execution_time": self.execution_time
        }

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
                
        # Result型を使用したエラーハンドリング
        result = controller.execute_command_result("Get-Process")
        if result.is_ok():
            print(result.unwrap())
        else:
            print(f"エラー: {result.unwrap_err()}")
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
        except PowerShellExecutionError as e:
            elapsed = time.time() - start_time
            return CommandResult(
                output="",
                error=str(e),
                success=False,
                command=command,
                execution_time=elapsed
            )
        except Exception as e:
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
        PowerShellスクリプトを非同期で実行します。
        
        Args:
            script: 実行するPowerShellスクリプト
            timeout: スクリプト実行のタイムアウト（秒）
            
        Returns:
            CommandResult: スクリプトの実行結果
        """
        # 内部的にはrun_commandを使用
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
            PowerShellExecutionError: コマンド実行時にエラーが発生した場合
            PowerShellTimeoutError: コマンド実行がタイムアウトした場合
        """
        loop = self._get_or_create_loop()
        coro = self.run_command(command, timeout)
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        
        cmd_timeout = timeout or self.settings.timeout.default
        try:
            result = future.result(timeout=cmd_timeout)
            if not result.success:
                raise PowerShellExecutionError(result.error, command)
            return result.output
        except TimeoutError:
            raise PowerShellTimeoutError("コマンド実行がタイムアウトしました", command, cmd_timeout)
    
    @as_result
    def execute_command_result(self, command: str, timeout: Optional[float] = None) -> Result[str, PowerShellError]:
        """
        PowerShellコマンドを実行し、Result型で結果を返します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            Result[str, PowerShellError]: 成功した場合はOk(output)、失敗した場合はErr(error)
        """
        return self.execute_command(command, timeout)
    
    def execute_script(self, script: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellスクリプトを実行します。複数行のスクリプトをサポートします。
        
        Args:
            script: 実行するPowerShellスクリプト
            timeout: スクリプト実行のタイムアウト（秒）
            
        Returns:
            str: スクリプトの実行結果
            
        Raises:
            PowerShellExecutionError: スクリプト実行時にエラーが発生した場合
            PowerShellTimeoutError: スクリプト実行がタイムアウトした場合
        """
        # コマンドの実行方法と同じ
        return self.execute_command(script, timeout)
    
    @as_result
    def execute_script_result(self, script: str, timeout: Optional[float] = None) -> Result[str, PowerShellError]:
        """
        PowerShellスクリプトを実行し、Result型で結果を返します。
        
        Args:
            script: 実行するPowerShellスクリプト
            timeout: スクリプト実行のタイムアウト（秒）
            
        Returns:
            Result[str, PowerShellError]: 成功した場合はOk(output)、失敗した場合はErr(error)
        """
        return self.execute_script(script, timeout)
    
    def get_json(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        PowerShellコマンドを実行し、結果をJSON形式で解析して返します。
        
        Args:
            command: 実行するPowerShellコマンド（ConvertTo-Jsonを使用するコマンド）
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            Dict[str, Any]: JSONデータを解析した辞書
            
        Raises:
            PowerShellExecutionError: コマンド実行時にエラーが発生した場合
            PowerShellTimeoutError: コマンド実行がタイムアウトした場合
            ValueError: JSON解析に失敗した場合
        """
        import json
        output = self.execute_command(command, timeout)
        return json.loads(output)
    
    def get_environment_variable(self, name: str) -> str:
        """
        PowerShell環境変数の値を取得します。
        
        Args:
            name: 環境変数名
            
        Returns:
            str: 環境変数の値
            
        Raises:
            PowerShellExecutionError: 環境変数が存在しない場合など
        """
        return self.execute_command(f"$env:{name}")
    
    def set_environment_variable(self, name: str, value: str) -> None:
        """
        PowerShell環境変数を設定します。
        
        Args:
            name: 環境変数名
            value: 設定する値
            
        Raises:
            PowerShellExecutionError: 環境変数の設定に失敗した場合
        """
        self.execute_command(f"$env:{name} = '{value.replace("'", "''")}'")
    
    def _get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """
        既存のイベントループを取得するか、新しいイベントループを作成します。
        
        Returns:
            asyncio.AbstractEventLoop: イベントループ
        """
        with self._lock:
            if self._loop is not None and self._loop.is_running():
                return self._loop
                
            # 既存のイベントループを探す
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                
            # イベントループが実行中でなければ、別のスレッドで実行
            if not self._loop.is_running():
                thread = threading.Thread(target=self._run_event_loop, args=(self._loop,), daemon=True)
                thread.start()
                
            return self._loop
    
    def _run_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        イベントループを実行します。
        
        Args:
            loop: 実行するイベントループ
        """
        asyncio.set_event_loop(loop)
        loop.run_forever()
    
    def __del__(self) -> None:
        """デストラクタ - リソースを適切に解放します"""
        try:
            self.close_sync()
        except Exception:
            pass 