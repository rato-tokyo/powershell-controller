"""
PowerShellコントローラーの設定クラス
"""
import os
import sys
from typing import Dict, Optional, List, Union, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

class RetryConfig(BaseModel):
    """リトライ設定"""
    max_attempts: int = Field(default=3, description="最大試行回数")
    base_delay: float = Field(default=1.0, description="初期待機時間（秒）")
    max_delay: float = Field(default=5.0, description="最大待機時間（秒）")
    jitter: float = Field(default=0.1, description="ジッター（ランダム化係数）")

class TimeoutConfig(BaseModel):
    """タイムアウト設定"""
    default: float = Field(default=30.0, description="デフォルトのタイムアウト時間（秒）")
    startup: float = Field(default=10.0, description="プロセス起動用のタイムアウト（秒）")
    execution: float = Field(default=5.0, description="コマンド実行用のタイムアウト（秒）")
    read: float = Field(default=0.5, description="キュー読み取り用のタイムアウト（秒）")
    shutdown: float = Field(default=5.0, description="シャットダウン用のタイムアウト（秒）")
    cleanup: float = Field(default=3.0, description="クリーンアップ用のタイムアウト（秒）")

class PowerShellConfig(BaseModel):
    """PowerShell固有の設定"""
    init_command: str = Field(
        default="""
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "PowerShell Controller Session"
Write-Output "SESSION_READY"
While ($true) {
    $command = Read-Host
    if ($command -eq "EXIT") { break }
    try {
        $result = Invoke-Expression -Command $command -ErrorAction Stop
        if ($null -ne $result) {
            try {
                # JSON変換を試みるが、失敗したら普通の文字列として出力
                $json = ConvertTo-Json -InputObject $result -Depth 5 -Compress -ErrorAction SilentlyContinue
                if ($null -ne $json) {
                    Write-Output $json
                } else {
                    Write-Output $result.ToString()
                }
            } catch {
                Write-Output $result.ToString()
            }
        }
        Write-Output "COMMAND_SUCCESS"
    } catch {
        $errorMessage = $_.Exception.Message
        Write-Error "ERROR: $errorMessage"
        Write-Output "COMMAND_ERROR"
    }
}
Write-Output "SESSION_END"
""",
        description="PowerShellの初期化コマンド"
    )
    
    standard_env_vars: Dict[str, str] = Field(
        default_factory=lambda: {
            "POWERSHELL_TELEMETRY_OPTOUT": "1",  # テレメトリを無効化
            "PSModulePath": "",  # モジュールパスをクリア
            "PATHEXT": ".COM;.EXE;.BAT;.CMD",  # 基本的な実行ファイル拡張子のみ
            "POWERSHELL_UPDATECHECK": "Off",  # 更新チェックを無効化
            "POWERSHELL_MANAGED_MODE": "Off",  # マネージドモードを無効化
            "POWERSHELL_BASIC_MODE": "On",  # 基本モードを有効化
            "POWERSHELL_DISABLE_EXTENSIONS": "1"  # 拡張機能を無効化
        },
        description="PowerShell実行時に設定する標準環境変数"
    )
    
    standard_args: List[str] = Field(
        default_factory=lambda: [
            "-Version", "5.1",
            "-NoLogo",
            "-NoProfile", 
            "-ExecutionPolicy", "Bypass",
            "-NoExit"
        ],
        description="PowerShell実行時に使用する標準引数"
    )

class LoggingConfig(BaseModel):
    """ログ設定"""
    format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="ログフォーマット"
    )
    level: str = Field(default="INFO", description="ログレベル")
    capture_stdout: bool = Field(default=True, description="標準出力をキャプチャするかどうか")

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
    log_file: Optional[str] = Field(
        default=None,
        description="ログファイルパス",
        json_schema_extra={"env": "PS_CTRL_LOG_FILE"}
    )
    
    # タイムアウト設定
    timeouts: TimeoutConfig = Field(
        default_factory=TimeoutConfig,
        description="タイムアウト設定"
    )
    
    # リトライ設定
    retry: RetryConfig = Field(
        default_factory=RetryConfig,
        description="リトライ設定"
    )
    
    # PowerShell設定
    powershell: PowerShellConfig = Field(
        default_factory=PowerShellConfig,
        description="PowerShell固有の設定"
    )
    
    # ログ設定
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="ログ設定"
    )
    
    # 環境変数
    env_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="PowerShellプロセスに渡す環境変数"
    )
    
    # 追加オプション
    additional_args: List[str] = Field(
        default_factory=list,
        description="PowerShellに渡す追加の引数"
    )
    
    # テスト用モック設定
    use_mock: bool = Field(
        default=False,
        description="テスト用にモックを使用するかどうか"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="PS_CTRL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def get_ps_path(self) -> str:
        """
        設定されたPowerShellのパス、または自動検出されたパスを返します。
        
        Returns:
            PowerShellの実行パス
        """
        if self.ps_path:
            return self.ps_path
        
        return self._get_default_ps_path()
    
    def _get_default_ps_path(self) -> str:
        """
        デフォルトのPowerShellパスを取得します。
        
        Returns:
            PowerShellの実行パス
        """
        if sys.platform == "win32":
            # PowerShell 7（pwsh.exe）を優先
            pwsh_paths = [
                os.path.expandvars("%ProgramFiles%\\PowerShell\\7\\pwsh.exe"),
                os.path.expandvars("%ProgramFiles(x86)%\\PowerShell\\7\\pwsh.exe"),
                # Windows PowerShell（powershell.exe）
                os.path.expandvars("%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe")
            ]
            
            for path in pwsh_paths:
                if os.path.exists(path):
                    return path
                    
            raise RuntimeError("PowerShell executable not found")
            
        else:
            # Linux/macOSの場合はpwshを使用
            return "pwsh"
    
    def get_all_env_vars(self) -> Dict[str, str]:
        """
        すべての環境変数を取得します。
        
        Returns:
            環境変数の辞書
        """
        # 基本の環境変数を取得
        env = os.environ.copy()
        
        # 標準の環境変数を適用
        env.update(self.powershell.standard_env_vars)
        
        # ユーザー定義の環境変数を適用（これにより標準設定を上書き可能）
        env.update(self.env_vars)
        
        return env
    
    def get_all_args(self) -> List[str]:
        """
        すべてのコマンドライン引数を取得します。
        
        Returns:
            引数のリスト
        """
        return self.powershell.standard_args + self.additional_args
    
    def update(self, **kwargs: Any) -> 'PowerShellControllerSettings':
        """
        設定を更新します。
        
        Args:
            **kwargs: 更新する設定
            
        Returns:
            更新された設定インスタンス
        """
        new_settings = self.model_copy(deep=True)
        for key, value in kwargs.items():
            if hasattr(new_settings, key):
                setattr(new_settings, key, value)
        return new_settings
    
    def with_env_vars(self, **env_vars: str) -> 'PowerShellControllerSettings':
        """
        新しい環境変数を追加した設定を返します。
        
        Args:
            **env_vars: 追加する環境変数
            
        Returns:
            更新された設定インスタンス
        """
        new_env_vars = self.env_vars.copy()
        new_env_vars.update(env_vars)
        return self.update(env_vars=new_env_vars)
    
    def with_args(self, *args: str) -> 'PowerShellControllerSettings':
        """
        新しい引数を追加した設定を返します。
        
        Args:
            *args: 追加する引数
            
        Returns:
            更新された設定インスタンス
        """
        new_args = self.additional_args.copy()
        new_args.extend(args)
        return self.update(additional_args=new_args)

__all__ = [
    'PowerShellControllerSettings',
    'RetryConfig',
    'TimeoutConfig',
    'PowerShellConfig',
    'LoggingConfig'
] 