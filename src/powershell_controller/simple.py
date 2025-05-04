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

class SimplePowerShellController:
    """PowerShell 7のセッション管理とコマンド実行を行うコントローラー"""
    
    def __init__(self):
        """PowerShell 7コントローラーを初期化"""
        self.ps_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
        self.logger = self._setup_logger()
        self.process = None
        self.pid = None
        
        if not os.path.exists(self.ps_path):
            raise FileNotFoundError(f"PowerShell 7が見つかりません: {self.ps_path}")
            
        try:
            result = self._run_simple_command("Write-Output 'PowerShell 7 Test'")
            if "PowerShell 7 Test" not in result:
                raise RuntimeError("PowerShell 7の動作確認に失敗しました")
        except Exception as e:
            self.logger.error(f"初期化に失敗しました: {e}")
            raise

    def _cleanup_process(self):
        """プロセスをクリーンアップ"""
        if self.pid is None:
            return

        try:
            process = psutil.Process(self.pid)
            process.terminate()
            process.wait(timeout=3)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            pass
        finally:
            self.pid = None
            self.process = None

    def _setup_logger(self):
        """基本的なロギングの設定"""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _run_simple_command(self, command, timeout=10):
        """
        シンプルなコマンド実行
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: タイムアウト時間（秒）
            
        Returns:
            str: コマンドの出力
        """
        try:
            self.process = subprocess.Popen(
                [self.ps_path, "-NoProfile", "-NonInteractive", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            self.pid = self.process.pid
            stdout, stderr = self.process.communicate(timeout=timeout)
            
            if self.process.returncode != 0:
                raise RuntimeError(f"コマンド実行エラー: {stderr}")
                
            return stdout
        except subprocess.TimeoutExpired:
            self._cleanup_process()
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
        """
        if not commands:
            return []
            
        markers = [f"CMD_END_{uuid.uuid4().hex}" for _ in range(len(commands))]
        script_content = "$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8\n"
        script_content += "$ErrorActionPreference = 'Stop'\n"
        
        for i, cmd in enumerate(commands):
            script_content += f"""
            try {{
                $result_{i} = {cmd}
                if ($null -ne $result_{i}) {{
                    $result_{i} | Out-String
                }}
                Write-Output '{markers[i]}'
            }} catch {{
                Write-Output "ERROR: $($_.Exception.Message)"
                Write-Output '{markers[i]}'
            }}
            """
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ps1', mode='w', encoding='utf-8') as temp:
                temp.write(script_content)
                script_file = temp.name
            
            self.process = subprocess.Popen(
                [self.ps_path, "-NoProfile", "-NonInteractive", "-File", script_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            self.pid = self.process.pid
            
            stdout, stderr = self.process.communicate(timeout=timeout)
            
            if self.process.returncode != 0:
                raise RuntimeError(f"スクリプト実行エラー: {stderr}")
            
            results = []
            current_output = []
            
            for line in stdout.splitlines():
                line = line.strip()
                if any(marker in line for marker in markers):
                    results.append('\n'.join(current_output))
                    current_output = []
                else:
                    current_output.append(line)
            
            if current_output:
                results.append('\n'.join(current_output))
                
            return results[:len(commands)]
            
        except Exception as e:
            self.logger.error(f"セッション実行エラー: {e}")
            raise
        finally:
            self._cleanup_process()
            if os.path.exists(script_file):
                os.unlink(script_file)

    def __del__(self):
        """デストラクタ：プロセスのクリーンアップ"""
        self._cleanup_process() 