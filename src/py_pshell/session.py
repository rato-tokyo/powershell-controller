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
            
        # モックモードかどうかを確認
        if self.settings.use_mock:
            logger.debug("モックモードでPowerShellセッションを開始します")
            self._is_running = True
            return
            
        try:
            # PowerShellプロセスの起動
            ps_path = self.settings.powershell.path
            ps_args = self.settings.get_all_args()
            env_vars = self.settings.get_all_env_vars()
            
            # 環境変数の準備
            env = os.environ.copy()
            env.update(env_vars)
            
            # プロセス起動時の設定
            startup_info = None
            if platform.system().lower() == "windows":
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = subprocess.SW_HIDE
            
            logger.debug(f"PowerShellプロセスを起動: {ps_path} {' '.join(ps_args)}")
            
            # プロセスを非同期モードで起動
            self.process = await asyncio.create_subprocess_exec(
                ps_path,
                *ps_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
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
            
        init_script = self.settings.powershell.init_script
        self._writer.write(init_script.encode(self.settings.powershell.encoding) + b"\n")
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
            
        # モックモードの場合は単に状態を更新
        if self.settings.use_mock:
            self._is_running = False
            logger.debug("モックモードのPowerShellセッションを停止しました")
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
                
                # 少し待ってからプロセスを強制終了
                try:
                    await asyncio.wait_for(self.process.wait(), self.settings.timeout.shutdown)
                except asyncio.TimeoutError:
                    logger.warning("PowerShellプロセスが時間内に終了しなかったため、強制終了します")
                    self.process.kill()
                
                # リソースをクリーンアップ
                if self._writer:
                    self._writer.close()
                    await self._writer.wait_closed()
                
                self.process = None
                self._reader = None
                self._writer = None
                self._is_running = False
                
                logger.info("PowerShellセッションが停止されました")
        
        except Exception as e:
            logger.error(f"PowerShellセッションの停止に失敗: {e}")
            self._is_running = False  # エラーでも状態をリセット
            raise PowerShellShutdownError(f"PowerShellセッションの停止に失敗しました: {e}")
    
    async def _read_line(self) -> str:
        """
        PowerShellからの出力を1行読み込みます。
        
        Returns:
            str: 読み込んだ行
            
        Raises:
            CommunicationError: 通信エラーが発生した場合
        """
        if not self._reader:
            raise CommunicationError("PowerShellプロセスと通信できません: ストリームが初期化されていません")
            
        try:
            line_bytes = await self._reader.readline()
            encoding = self.settings.powershell.encoding
            try:
                # まずは指定されたエンコーディングでデコード
                line = line_bytes.decode(encoding).strip()
            except UnicodeDecodeError:
                # エラーが発生した場合は代替のエンコーディングで試みる
                fallback_encodings = ["utf-8", "cp932", "shift-jis", "euc-jp"]
                for enc in fallback_encodings:
                    if enc != encoding:
                        try:
                            line = line_bytes.decode(enc).strip()
                            logger.debug(f"代替エンコーディング {enc} でデコードに成功")
                            break
                        except UnicodeDecodeError:
                            continue
                else:
                    # すべて失敗した場合はエラーを発生
                    line = line_bytes.decode(encoding, errors="replace").strip()
                    logger.warning(f"適切なエンコーディングが見つからないため、置換モードでデコード: {line}")
            
            return line
        except Exception as e:
            raise CommunicationError(f"PowerShellからの読み込みに失敗: {e}")
    
    async def execute(self, command: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellコマンドを実行し、結果を返します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            str: コマンドの実行結果
            
        Raises:
            PowerShellExecutionError: コマンド実行時にエラーが発生した場合
            PowerShellTimeoutError: コマンド実行がタイムアウトした場合
            CommunicationError: PowerShellプロセスとの通信エラー
        """
        # セッションが実行中でなければ開始
        if not self._is_running:
            await self.start()
        
        # モックモードの場合はモック応答を返す
        if self.settings.use_mock:
            logger.debug(f"モックモードでコマンドを実行: {command}")
            return f"モック出力: {command}"
        
        if not self._writer or not self._reader:
            raise CommunicationError("PowerShellプロセスと通信できません: ストリームが初期化されていません")
        
        # タイムアウト値の設定
        if timeout is None:
            timeout = self.settings.timeout.execution
        
        try:
            # コマンドを送信
            logger.debug(f"コマンドを実行: {command}")
            
            # 特殊文字をエスケープ
            escaped_cmd = command.replace('"', '`"').replace('$', '`$')
            
            # __ExecuteCommandラッパー関数を使用
            wrapped_cmd = f"__ExecuteCommand \"{escaped_cmd}\""
            self._writer.write(f"{wrapped_cmd}\n".encode(self.settings.powershell.encoding))
            await self._writer.drain()
            
            # 応答の読み取り
            output_lines = []
            command_completed = False
            
            while not command_completed:
                try:
                    line = await asyncio.wait_for(self._read_line(), timeout)
                    
                    # 終了マーカーをチェック
                    if line == "COMMAND_SUCCESS":
                        command_completed = True
                        continue
                    elif line == "COMMAND_ERROR":
                        error_message = "\n".join(output_lines)
                        raise PowerShellExecutionError(error_message, command)
                    
                    # 通常の出力行を追加
                    output_lines.append(line)
                    
                except asyncio.TimeoutError:
                    logger.error(f"コマンド実行がタイムアウトしました（{timeout}秒）: {command}")
                    raise PowerShellTimeoutError("コマンド実行がタイムアウトしました", command, timeout)
            
            # 結果を返す
            result = "\n".join(output_lines).strip()
            logger.debug(f"コマンド実行結果: {result}")
            return result
            
        except PowerShellExecutionError:
            # 既に適切なエラーが発生しているので再スロー
            raise
            
        except Exception as e:
            logger.error(f"コマンド実行中にエラーが発生: {e}")
            raise PowerShellExecutionError(f"コマンド実行中にエラーが発生しました: {e}", command) 