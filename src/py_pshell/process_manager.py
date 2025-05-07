"""
PowerShellプロセス管理モジュール

PowerShellプロセスの起動と終了を管理する機能を提供します。
"""
import os
import sys
import asyncio
import platform
import subprocess
from typing import Optional, Tuple
from loguru import logger

from .config import PowerShellControllerSettings
from .utils.session_util import get_process_startup_info
from .errors import (
    PowerShellError,
    PowerShellStartupError,
    PowerShellShutdownError
)

class ProcessManager:
    """
    PowerShellプロセス管理クラス
    
    PowerShellプロセスの起動と終了を管理します。
    """
    
    def __init__(self, settings: PowerShellControllerSettings):
        """
        プロセス管理クラスを初期化します。
        
        Args:
            settings: セッションの設定
        """
        self.settings = settings
        self.process: Optional[subprocess.Popen] = None
        self._is_running = False
        logger.debug("ProcessManagerが初期化されました")
    
    async def start(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """
        PowerShellプロセスを開始します。
        
        Returns:
            Tuple[asyncio.StreamReader, asyncio.StreamWriter]: 標準出力と標準入力のストリーム
            
        Raises:
            PowerShellStartupError: PowerShellプロセスの起動に失敗した場合
        """
        if self._is_running:
            logger.debug("PowerShellプロセスは既に実行中です")
            return None, None
            
        try:
            # PowerShellプロセスの起動
            ps_path = self.settings.powershell_executable
            ps_args = self.settings.arguments
            
            # プロセス起動時の設定を取得
            startup_info = get_process_startup_info()
            
            logger.debug(f"PowerShellプロセスを起動: {ps_path} {' '.join(ps_args)}")
            
            # プロセスを非同期モードで起動
            self.process = await asyncio.create_subprocess_exec(
                ps_path,
                *ps_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                startupinfo=startup_info
            )
            
            if not self.process or not self.process.stdin or not self.process.stdout:
                raise PowerShellStartupError("PowerShellプロセスの起動に失敗しました: プロセスまたはストリームが作成できませんでした")
            
            self._is_running = True
            logger.info("PowerShellプロセスが開始されました")
            
            return self.process.stdout, self.process.stdin
        
        except Exception as e:
            logger.error(f"PowerShellプロセスの開始に失敗: {e}")
            raise PowerShellStartupError(f"PowerShellプロセスの開始に失敗しました: {e}")
    
    async def stop(self) -> None:
        """
        PowerShellプロセスを停止します。
        
        Raises:
            PowerShellShutdownError: PowerShellプロセスの終了に失敗した場合
        """
        if not self._is_running:
            logger.debug("PowerShellプロセスは実行されていません")
            return
            
        try:
            if self.process:
                # プロセスの終了を待機
                try:
                    await asyncio.wait_for(
                        self.process.wait(),
                        self.settings.timeout.shutdown
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"PowerShellの通常終了がタイムアウトしました。強制終了します。")
                    self.process.kill()
                    
                # クリーンアップ
                self.process = None
                self._is_running = False
                
                logger.info("PowerShellプロセスが停止しました")
                
        except Exception as e:
            logger.error(f"PowerShellプロセスの停止に失敗: {e}")
            raise PowerShellShutdownError(f"PowerShellプロセスの停止に失敗しました: {e}")
    
    @property
    def is_running(self) -> bool:
        """
        プロセスが実行中かどうかを返します。
        
        Returns:
            bool: プロセスが実行中かどうか
        """
        return self._is_running 