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
from concurrent.futures import ThreadPoolExecutor

from .interfaces import CommandResultProtocol, PowerShellControllerProtocol
from .config import PowerShellControllerSettings
from .session import PowerShellSession
from .utils.command_result import CommandResult
from .command_executor import CommandExecutor
from .json_handler import JsonHandler
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
        self._executor = CommandExecutor(self.settings)
        self._json_handler = JsonHandler()
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
            loop = asyncio.get_event_loop()
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
        
        return await self._executor.run_command(self.session, command, timeout)
    
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
        if not self.session:
            self.session = PowerShellSession(settings=self.settings)
            asyncio.run(self.session.__aenter__())
        
        return self._executor.execute_command(self.session, command, timeout)
    
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
        command = self._json_handler.ensure_json_command(command)
        output = self.execute_command(command, timeout)
        return self._json_handler.get_json(command, output)
    
    def __del__(self) -> None:
        """デストラクタ"""
        if self.session:
            try:
                self.close_sync()
            except Exception as e:
                logger.error(f"セッションのクローズに失敗: {e}") 