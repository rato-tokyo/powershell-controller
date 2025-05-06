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
    timeout: float = Field(
        default=30.0,
        description="デフォルトのタイムアウト時間（秒）",
        json_schema_extra={"env": "PS_CTRL_TIMEOUT"}
    )
    
    # リトライ設定
    retry_config: RetryConfig = Field(
        default_factory=RetryConfig,
        description="リトライ設定"
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
        環境変数を追加した新しい設定を作成します。
        
        Args:
            **env_vars: 追加する環境変数
            
        Returns:
            新しい設定インスタンス
        """
        new_settings = self.model_copy(deep=True)
        new_settings.env_vars.update(env_vars)
        return new_settings 