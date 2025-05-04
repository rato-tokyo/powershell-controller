"""
シンプルなPowerShell 7コントローラー
MCPのためのセッション管理とコマンド実行に特化
"""
import subprocess
import os
import sys
import logging
import tempfile
import uuid
import time
import psutil
from logging.handlers import RotatingFileHandler

class PowerShellError(Exception):
    """PowerShell実行に関連するエラーの基底クラス"""
    pass

class PowerShellNotFoundError(PowerShellError):
    """PowerShell 7が見つからない場合のエラー"""
    pass

class PowerShellExecutionError(PowerShellError):
    """PowerShellコマンドの実行に失敗した場合のエラー"""
    def __init__(self, message, command=None, stderr=None):
        super().__init__(message)
        self.command = command
        self.stderr = stderr

class PowerShellTimeoutError(PowerShellError):
    """PowerShellコマンドがタイムアウトした場合のエラー"""
    pass

class SimplePowerShellController:
    """PowerShell 7のセッション管理とコマンド実行を行うコントローラー"""
    
    def __init__(self, log_level=logging.INFO, log_file=None, max_log_size=10*1024*1024):
        """
        PowerShell 7コントローラーを初期化
        
        Args:
            log_level: ログレベル（デフォルト：INFO）
            log_file: ログファイルのパス（デフォルト：None）
            max_log_size: ログファイルの最大サイズ（デフォルト：10MB）
        """
        self.ps_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
        self.logger = self._setup_logger(log_level, log_file, max_log_size)
        self.process = None
        self.pid = None
        
        if not os.path.exists(self.ps_path):
            self.logger.error(f"PowerShell 7が見つかりません: {self.ps_path}")
            raise FileNotFoundError(f"PowerShell 7が見つかりません: {self.ps_path}")
            
        try:
            self.logger.info("PowerShell 7の動作確認を開始")
            result = self._run_simple_command("Write-Output 'PowerShell 7 Test'")
            if "PowerShell 7 Test" not in result:
                self.logger.error("PowerShell 7の動作確認に失敗しました")
                raise RuntimeError("PowerShell 7の動作確認に失敗しました")
            self.logger.info("PowerShell 7の動作確認が完了しました")
        except Exception as e:
            self.logger.error(f"初期化に失敗しました: {e}")
            raise

    def _cleanup_process(self):
        """
        プロセスをクリーンアップ
        
        子プロセスも含めて確実に終了させる
        """
        if self.pid is None:
            return

        try:
            process = psutil.Process(self.pid)
            
            # 子プロセスを取得して終了
            children = process.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            
            # メインプロセスを終了
            process.terminate()
            
            # プロセスの終了を待機
            gone, alive = psutil.wait_procs([process] + children, timeout=3)
            
            # 残っているプロセスを強制終了
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
                
            self.logger.debug(f"プロセス {self.pid} とその子プロセスを終了しました")
            
        except psutil.NoSuchProcess:
            self.logger.debug(f"プロセス {self.pid} は既に終了しています")
        except Exception as e:
            self.logger.error(f"プロセスのクリーンアップ中にエラーが発生: {e}")
        finally:
            self.pid = None
            self.process = None
    
    def _setup_logger(self, log_level, log_file, max_log_size):
        """
        ロギングの設定
        
        Args:
            log_level: ログレベル
            log_file: ログファイルのパス
            max_log_size: ログファイルの最大サイズ
            
        Returns:
            logging.Logger: 設定済みのロガー
        """
        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
        
        if not logger.handlers:
            # コンソールハンドラーの設定
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - [%(process)d] %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # ファイルハンドラーの設定（指定された場合）
            if log_file:
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_log_size,
                    backupCount=5,
                    encoding='utf-8'
                )
                file_handler.setLevel(log_level)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - [%(process)d] - %(funcName)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
        
        return logger
    
    def _run_simple_command(self, command, timeout=10):
        """
        シンプルなコマンド実行
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: タイムアウト時間（秒）
            
        Returns:
            str: コマンドの出力
            
        Raises:
            PowerShellExecutionError: コマンド実行に失敗した場合
            PowerShellTimeoutError: タイムアウトした場合
        """
        self.logger.debug(f"コマンド実行開始: {command}")
        start_time = time.time()
        
        try:
            self.process = subprocess.Popen(
                [self.ps_path, "-NoProfile", "-NonInteractive", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            self.pid = self.process.pid
            self.logger.debug(f"プロセス開始 (PID: {self.pid})")
            
            stdout, stderr = self.process.communicate(timeout=timeout)
            
            if self.process.returncode != 0:
                raise PowerShellExecutionError(
                    f"コマンド実行エラー (終了コード: {self.process.returncode})",
                    command=command,
                    stderr=stderr
                )
            
            execution_time = time.time() - start_time
            self.logger.debug(f"コマンド実行完了 (実行時間: {execution_time:.2f}秒)")
            return stdout
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"コマンドがタイムアウトしました: {command}")
            self._cleanup_process()
            raise PowerShellTimeoutError(f"コマンドがタイムアウトしました (timeout: {timeout}秒)")
        except Exception as e:
            self.logger.error(f"コマンド実行中に予期せぬエラーが発生: {e}")
            raise
        finally:
            self._cleanup_process()
    
    def execute_command(self, command, timeout=10):
        """
        PowerShellコマンドを実行
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: タイムアウト時間（秒）
            
        Returns:
            str: コマンド実行結果
        """
        try:
            wrapped_command = f"""
            try {{
                $ErrorActionPreference = 'Stop'
                $OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
                $result = {command}
                if ($null -ne $result) {{
                    $result | Out-String
                }}
            }} catch {{
                Write-Error "$($_.Exception.Message)"
                exit 1
            }}
            """
            return self._run_simple_command(wrapped_command, timeout)
        except Exception as e:
            self.logger.error(f"コマンド実行エラー: {e}")
            raise
    
    def execute_commands_in_session(self, commands, timeout=30):
        """
        複数のコマンドをセッションを維持して実行
        
        Args:
            commands: 実行するコマンドのリスト
            timeout: タイムアウト時間（秒）
            
        Returns:
            list: 各コマンドの実行結果
            
        Raises:
            PowerShellExecutionError: コマンド実行に失敗した場合
            PowerShellTimeoutError: タイムアウトした場合
        """
        if not commands:
            self.logger.warning("実行するコマンドが指定されていません")
            return []
            
        self.logger.info(f"{len(commands)}個のコマンドをセッションで実行開始")
        start_time = time.time()
        script_file = None
            
        markers = [f"CMD_END_{uuid.uuid4().hex}" for _ in range(len(commands))]
        script_content = "$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8\n"
        script_content += "$ErrorActionPreference = 'Stop'\n"
        script_content += "$ProgressPreference = 'SilentlyContinue'\n"  # 進行状況の表示を抑制
        
        for i, cmd in enumerate(commands):
            script_content += f"""
            try {{
                $result_{i} = {cmd}
                if ($null -ne $result_{i}) {{
                    $result_{i} | Out-String
                }}
                Write-Output '{markers[i]}'
            }} catch {{
                Write-Error "コマンド実行エラー (インデックス: {i}): $($_.Exception.Message)"
                Write-Output '{markers[i]}'
            }}
            """
        
        try:
            # 一時スクリプトファイルの作成
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ps1', mode='w', encoding='utf-8') as temp:
                temp.write(script_content)
                script_file = temp.name
                self.logger.debug(f"一時スクリプトファイルを作成: {script_file}")
            
            # スクリプトの実行
            self.process = subprocess.Popen(
                [self.ps_path, "-NoProfile", "-NonInteractive", "-File", script_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            self.pid = self.process.pid
            self.logger.debug(f"セッションプロセス開始 (PID: {self.pid})")
            
            stdout, stderr = self.process.communicate(timeout=timeout)
            
            if self.process.returncode != 0:
                self.logger.error(f"スクリプト実行エラー: {stderr}")
                raise PowerShellExecutionError(
                    "スクリプト実行エラー",
                    command="複数コマンドセッション",
                    stderr=stderr
                )
            
            # 結果の解析
            results = []
            current_output = []
            error_found = False
            
            for line in stdout.splitlines():
                line = line.strip()
                if "ERROR: " in line:
                    error_found = True
                if any(marker in line for marker in markers):
                    results.append('\n'.join(current_output))
                    current_output = []
                else:
                    current_output.append(line)
            
            if current_output:
                results.append('\n'.join(current_output))
            
            execution_time = time.time() - start_time
            self.logger.info(f"セッション実行完了 (実行時間: {execution_time:.2f}秒)")
            
            if error_found:
                self.logger.warning("一部のコマンドでエラーが発生しました")
                
            return results[:len(commands)]
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"セッションがタイムアウトしました (timeout: {timeout}秒)")
            self._cleanup_process()
            raise PowerShellTimeoutError(f"セッションがタイムアウトしました (timeout: {timeout}秒)")
        except Exception as e:
            self.logger.error(f"セッション実行中に予期せぬエラーが発生: {e}")
            raise
        finally:
            self._cleanup_process()
            if script_file and os.path.exists(script_file):
                try:
                    os.unlink(script_file)
                    self.logger.debug("一時スクリプトファイルを削除しました")
                except Exception as e:
                    self.logger.warning(f"一時スクリプトファイルの削除に失敗: {e}")

    def __del__(self):
        """デストラクタ：プロセスのクリーンアップ"""
        self._cleanup_process() 