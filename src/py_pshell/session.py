"""
PowerShellセッション管理モジュール

PowerShellとの接続セッションを管理するためのクラスを提供します。
"""
from typing import Optional
from loguru import logger

from .config import PowerShellControllerSettings
from .process_manager import ProcessManager
from .stream_handler import StreamHandler
from .errors import (
    PowerShellError,
    PowerShellStartupError,
    PowerShellShutdownError
)

class PowerShellSession:
    """
    PowerShellセッションクラス
    PowerShellとの通信セッションを管理します。
    """
    def __init__(self, settings: Optional[PowerShellControllerSettings] = None):
        """
        PowerShellSessionを初期化します。

        Args:
            settings: セッションの設定。Noneの場合はデフォルト設定が使用されます。
        """
        self.settings = settings or PowerShellControllerSettings()
        self._process_manager = ProcessManager(self.settings)
        self._stream_handler = StreamHandler(self.settings)
        logger.debug("PowerShellSessionが初期化されました")
        
    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリーポイント"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了処理"""
        await self.stop()
        
    async def start(self) -> None:
        """
        PowerShellセッションを開始します。
        
        Raises:
            PowerShellStartupError: PowerShellプロセスの起動に失敗した場合
        """
        if self._process_manager.is_running:
            logger.debug("PowerShellセッションは既に実行中です")
            return
            
        try:
            # プロセスを開始
            reader, writer = await self._process_manager.start()
            if not reader or not writer:
                raise PowerShellStartupError("PowerShellプロセスの起動に失敗しました")
            
            # ストリームを設定
            self._stream_handler.set_streams(reader, writer)
            
            # 初期化スクリプトを送信
            await self._stream_handler.send_init_script()
            
            # 準備完了を待機
            await self._stream_handler.wait_for_ready()
            
            logger.info("PowerShellセッションが開始されました")
        
        except Exception as e:
            logger.error(f"PowerShellセッションの開始に失敗: {e}")
            raise PowerShellStartupError(f"PowerShellセッションの開始に失敗しました: {e}")
    
    async def stop(self) -> None:
        """
        PowerShellセッションを停止します。
        
        Raises:
            PowerShellShutdownError: PowerShellプロセスの終了に失敗した場合
        """
        if not self._process_manager.is_running:
            logger.debug("PowerShellセッションは実行されていません")
            return
            
        try:
            # ストリームを閉じる
            await self._stream_handler.close()
            
            # プロセスを停止
            await self._process_manager.stop()
            
            logger.info("PowerShellセッションが停止しました")
                
        except Exception as e:
            logger.error(f"PowerShellセッションの停止に失敗: {e}")
            raise PowerShellShutdownError(f"PowerShellセッションの停止に失敗しました: {e}")
    
    async def execute(self, command: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellコマンドを実行します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            str: コマンドの実行結果
            
        Raises:
            PowerShellExecutionError: コマンドの実行に失敗した場合
            PowerShellTimeoutError: コマンドの実行がタイムアウトした場合
            CommunicationError: PowerShellとの通信に失敗した場合
        """
        return await self._stream_handler.execute_command(command, timeout) 