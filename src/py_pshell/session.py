"""
PowerShellセッション管理モジュール

PowerShellとの接続セッションを管理するためのクラスを提供します。
"""
import os
import sys
import asyncio
import platform
import subprocess
from typing import Optional, List, Dict, Any
from loguru import logger
import tempfile

from .config import PowerShellControllerSettings
from .utils.session_util import INIT_SCRIPT, get_process_startup_info, prepare_command_execution, parse_command_result
from .errors import (
    PowerShellError,
    PowerShellStartupError,
    PowerShellShutdownError,
    PowerShellExecutionError,
    PowerShellTimeoutError,
    CommunicationError
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
        self.process: Optional[subprocess.Popen] = None
        self._is_running = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        
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
        if self._is_running:
            logger.debug("PowerShellセッションは既に実行中です")
            return
            
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
            
            self._reader = self.process.stdout
            self._writer = self.process.stdin
            self._is_running = True
            
            # 初期化スクリプトの実行
            await self._send_init_script()
            await self._wait_for_ready()
            
            logger.info("PowerShellセッションが開始されました")
        
        except Exception as e:
            logger.error(f"PowerShellセッションの開始に失敗: {e}")
            raise PowerShellStartupError(f"PowerShellセッションの開始に失敗しました: {e}")
    
    async def _send_init_script(self) -> None:
        """
        初期化スクリプトを送信します。
        """
        if not self._writer:
            return
            
        init_script = INIT_SCRIPT
        self._writer.write(init_script.encode(self.settings.encoding) + b"\n")
        await self._writer.drain()
        logger.debug("初期化スクリプトを送信しました")
    
    async def _wait_for_ready(self) -> None:
        """
        PowerShellセッションの準備ができるのを待ちます。
        """
        if not self._reader:
            return
            
        timeout = self.settings.timeout.startup
        try:
            # "SESSION_READY" の応答を待つ
            line = await asyncio.wait_for(self._read_line(), timeout)
            if "SESSION_READY" not in line:
                logger.warning(f"予期しない初期化応答: {line}")
                
        except asyncio.TimeoutError:
            logger.error(f"PowerShellセッションの初期化がタイムアウトしました（{timeout}秒）")
            raise PowerShellTimeoutError("PowerShellセッションの初期化がタイムアウトしました", "初期化", timeout)
    
    async def stop(self) -> None:
        """
        PowerShellセッションを停止します。
        
        Raises:
            PowerShellShutdownError: PowerShellプロセスの終了に失敗した場合
        """
        if not self._is_running:
            logger.debug("PowerShellセッションは実行されていません")
            return
            
        try:
            if self.process:
                # 終了コマンドを送信
                if self._writer:
                    try:
                        self._writer.write(b"exit\n")
                        await self._writer.drain()
                    except Exception as e:
                        logger.warning(f"終了コマンドの送信に失敗: {e}")
                
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
                self._reader = None
                self._writer = None
                self.process = None
                self._is_running = False
                
                logger.info("PowerShellセッションが停止しました")
                
        except Exception as e:
            logger.error(f"PowerShellセッションの停止に失敗: {e}")
            raise PowerShellShutdownError(f"PowerShellセッションの停止に失敗しました: {e}")
    
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
        if not self._is_running or not self._writer or not self._reader:
            await self.start()
        
        try:
            # コマンドをPowerShellのラッパー関数で実行
            cmd_to_execute = prepare_command_execution(command)
            
            # コマンドをPowerShellに送信
            self._writer.write(f"{cmd_to_execute}\n".encode(self.settings.encoding))
            await self._writer.drain()
            
            # 結果を読み取り
            output_lines = await self._read_until_marker(timeout)
            success, result_text = parse_command_result(output_lines)
            
            if not success:
                logger.error(f"PowerShellコマンド実行エラー: {result_text}")
                raise PowerShellExecutionError(result_text, command)
                
            return result_text
            
        except Exception as e:
            if isinstance(e, PowerShellError):
                # 既知のエラーはそのまま再スロー
                raise
                
            logger.error(f"PowerShellコマンド実行中の予期しないエラー: {e}")
            raise PowerShellExecutionError(f"PowerShellコマンド実行中の予期しないエラー: {e}", command) 