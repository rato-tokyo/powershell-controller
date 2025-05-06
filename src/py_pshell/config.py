"""
PowerShellコントローラーの設定クラス

このモジュールはPowerShellコントローラーの設定クラスを提供します。
"""
import os
import sys
import platform
from typing import Dict, Optional, List, Union, Any
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

class TimeoutConfig(BaseModel):
    """タイムアウト設定"""
    default: float = Field(default=30.0, description="デフォルトのタイムアウト時間（秒）")
    startup: float = Field(default=10.0, description="プロセス起動用のタイムアウト（秒）")
    execution: float = Field(default=5.0, description="コマンド実行用のタイムアウト（秒）")
    shutdown: float = Field(default=5.0, description="シャットダウン用のタイムアウト（秒）")

class PowerShellConfig(BaseModel):
    """PowerShell固有の設定"""
    path: str = Field(
        default="",
        description="PowerShellの実行パス"
    )
    
    args: List[str] = Field(
        default_factory=lambda: [
            "-NoProfile", 
            "-ExecutionPolicy", "Bypass",
            "-NoLogo"
        ],
        description="PowerShell実行時の引数"
    )
    
    encoding: str = Field(
        default="cp932" if platform.system().lower() == "windows" and platform.release() == "10" else "utf-8",
        description="PowerShellプロセスとの通信に使用するエンコーディング"
    )
    
    init_script: str = Field(
        default="""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::GetEncoding('cp932')
    $OutputEncoding = [System.Text.Encoding]::GetEncoding('cp932')
} catch {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
}
$Host.UI.RawUI.WindowTitle = "PowerShell Controller Session"

# 終了マーカーの設定
function prompt {
    # 標準のプロンプトを削除して表示をクリーンに
    return ""
}

# 終了ステータスを示す関数
function global:__SetCommandStatus {
    param([bool]$success)
    if ($success) {
        Write-Output "COMMAND_SUCCESS"
    } else {
        Write-Output "COMMAND_ERROR"
    }
}

# コマンド実行のラッパー関数
function global:__ExecuteCommand {
    param([string]$cmd)
    try {
        # コマンドを実行してパイプラインの最後まで全ての出力を取得
        $result = Invoke-Expression $cmd | Out-String
        Write-Output $result
        __SetCommandStatus $true
    } catch {
        Write-Output "Error: $_"
        __SetCommandStatus $false
    }
}

Write-Output "SESSION_READY"
""",
        description="PowerShellの初期化スクリプト"
    )
    
    env_vars: Dict[str, str] = Field(
        default_factory=lambda: {
            "POWERSHELL_TELEMETRY_OPTOUT": "1",
            "POWERSHELL_UPDATECHECK": "Off",
        },
        description="PowerShell実行時に設定する環境変数"
    )

class PowerShellControllerSettings(BaseSettings):
    """PowerShellコントローラーの設定"""
    
    # PowerShellの実行パス
    ps_path: str = Field(
        default="",
        description="PowerShellの実行パス",
        json_schema_extra={"env": "PS_CTRL_PS_PATH"}
    )
    
    # ログ設定
    log_level: str = Field(
        default="INFO",
        description="ログレベル",
        json_schema_extra={"env": "PS_CTRL_LOG_LEVEL"}
    )
    
    # タイムアウト設定
    timeout: TimeoutConfig = Field(
        default_factory=TimeoutConfig,
        description="タイムアウト設定"
    )
    
    # PowerShell設定
    powershell: PowerShellConfig = Field(
        default_factory=PowerShellConfig,
        description="PowerShell固有の設定"
    )
    
    # 環境変数
    env_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="環境変数"
    )
    
    # テスト用モック設定
    use_mock: bool = Field(
        default=False,
        description="テスト用にモックを使用するかどうか"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="PS_CTRL_",
        env_nested_delimiter="__",
        extra="ignore"
    )
    
    @model_validator(mode='after')
    def validate_ps_path(self) -> 'PowerShellControllerSettings':
        """PowerShellパスの検証と設定"""
        if not self.ps_path:
            self.ps_path = self._get_default_ps_path()
            
        if self.powershell.path == "":
            self.powershell.path = self.ps_path
            
        return self
    
    def _get_default_ps_path(self) -> str:
        """
        プラットフォームに応じてデフォルトのPowerShellパスを取得します。
        Windows: pwsh.exe (PowerShell 7) または powershell.exe (Windows PowerShell)
        他のプラットフォーム: pwsh
        """
        system = platform.system().lower()
        
        if system == "windows":
            # PowerShell 7 (pwsh.exe)を優先
            pwsh_path = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "PowerShell", "7", "pwsh.exe")
            if os.path.exists(pwsh_path):
                return pwsh_path
                
            # Windows PowerShell (powershell.exe)
            return r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        else:
            # Linux/macOS
            return "pwsh"
            
    def get_all_env_vars(self) -> Dict[str, str]:
        """
        すべての環境変数を取得します。
        PowerShell設定の環境変数とコントローラー設定の環境変数をマージします。
        """
        env_vars = self.powershell.env_vars.copy()
        env_vars.update(self.env_vars)
        return env_vars
        
    def get_all_args(self) -> List[str]:
        """
        すべてのコマンドライン引数を取得します。
        """
        return self.powershell.args.copy()
        
    def update(self, **kwargs: Any) -> 'PowerShellControllerSettings':
        """
        設定を更新します。
        
        Args:
            **kwargs: 更新する設定の名前と値
            
        Returns:
            PowerShellControllerSettings: 更新された設定
        """
        for key, value in kwargs.items():
            setattr(self, key, value)
            
        return self 