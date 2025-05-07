"""
PowerShellストリーム処理モジュール

PowerShellとの通信ストリームを処理する機能を提供します。
"""
import asyncio
from typing import Optional, List
from loguru import logger

from .config import PowerShellControllerSettings
from .utils.session_util import INIT_SCRIPT, parse_command_result
from .errors import (
    PowerShellError,
    PowerShellTimeoutError,
    CommunicationError
)

class StreamHandler:
    """
    PowerShellストリーム処理クラス
    
    PowerShellとの通信ストリームを処理します。
    """
    
    def __init__(self, settings: PowerShellControllerSettings):
        """
        ストリーム処理クラスを初期化します。
        
        Args:
            settings: セッションの設定
        """
        self.settings = settings
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        logger.debug("StreamHandlerが初期化されました")
    
    def set_streams(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        ストリームを設定します。
        
        Args:
            reader: 標準出力のストリーム
            writer: 標準入力のストリーム
        """
        self._reader = reader
        self._writer = writer
    
    async def send_init_script(self) -> None:
        """
        初期化スクリプトを送信します。
        """
        if not self._writer:
            return
            
        init_script = INIT_SCRIPT
        self._writer.write(init_script.encode(self.settings.encoding) + b"\n")
        await self._writer.drain()
        logger.debug("初期化スクリプトを送信しました")
    
    async def wait_for_ready(self) -> None:
        """
        PowerShellセッションの準備ができるのを待ちます。
        """
        if not self._reader:
            return
            
        timeout = self.settings.timeout.startup
        try:
            # "SESSION_READY" の応答を待つ
            line = await self._read_line()
            if "SESSION_READY" not in line:
                logger.warning(f"予期しない初期化応答: {line}")
                
        except asyncio.TimeoutError:
            logger.error(f"PowerShellセッションの初期化がタイムアウトしました（{timeout}秒）")
            raise PowerShellTimeoutError("PowerShellセッションの初期化がタイムアウトしました", "初期化", timeout)
    
    async def _read_line(self) -> str:
        """
        PowerShellの出力から1行を読み取ります。
        
        Returns:
            str: 読み取った行
            
        Raises:
            CommunicationError: 読み取りに失敗した場合
        """
        if not self._reader:
            raise CommunicationError("PowerShellストリームが利用できません")
            
        try:
            line = await self._reader.readline()
            return line.decode(self.settings.encoding).rstrip('\r\n')
        except Exception as e:
            raise CommunicationError(f"PowerShellからの読み取りに失敗しました: {e}")
    
    async def _read_until_marker(self, timeout: Optional[float] = None) -> List[str]:
        """
        PowerShellの出力をステータスマーカーまで読み取ります。
        
        Args:
            timeout: 読み取りのタイムアウト（秒）
            
        Returns:
            List[str]: 読み取った行のリスト
            
        Raises:
            PowerShellTimeoutError: 読み取りがタイムアウトした場合
            CommunicationError: 読み取りに失敗した場合
        """
        timeout_value = timeout or self.settings.timeout.default
        output_lines = []
        
        try:
            async def read_output():
                """非同期で出力を読み取る"""
                while True:
                    line = await self._read_line()
                    output_lines.append(line)
                    
                    # ステータスマーカーが見つかれば終了
                    if line.strip() in ["COMMAND_SUCCESS", "COMMAND_ERROR"]:
                        return
            
            # タイムアウト付きで読み取り
            await asyncio.wait_for(read_output(), timeout_value)
            return output_lines
            
        except asyncio.TimeoutError:
            logger.warning(f"PowerShellコマンドの実行がタイムアウトしました（{timeout_value}秒）")
            raise PowerShellTimeoutError("PowerShellコマンドの実行がタイムアウトしました", "command", timeout_value)
            
        except Exception as e:
            if isinstance(e, PowerShellError):
                raise
            
            logger.error(f"PowerShellセッションでの読み取りエラー: {e}")
            raise CommunicationError(f"PowerShellセッションでの読み取りエラー: {e}")
    
    async def execute_command(self, command: str, timeout: Optional[float] = None) -> str:
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
        if not self._writer:
            raise CommunicationError("PowerShellストリームが利用できません")
            
        try:
            # コマンドを送信
            self._writer.write(command.encode(self.settings.encoding) + b"\n")
            await self._writer.drain()
            
            # 出力を読み取り
            output_lines = await self._read_until_marker(timeout)
            
            # 結果を解析
            return parse_command_result(output_lines)
            
        except Exception as e:
            if isinstance(e, PowerShellError):
                raise
            
            logger.error(f"PowerShellコマンドの実行に失敗: {e}")
            raise CommunicationError(f"PowerShellコマンドの実行に失敗しました: {e}")
    
    async def close(self) -> None:
        """
        ストリームを閉じます。
        """
        if self._writer:
            try:
                self._writer.write(b"exit\n")
                await self._writer.drain()
            except Exception as e:
                logger.warning(f"終了コマンドの送信に失敗: {e}")
            
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                logger.warning(f"ストリームのクローズに失敗: {e}")
            
            self._reader = None
            self._writer = None 