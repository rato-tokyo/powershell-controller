"""
PowerShellコントローラーの設定クラス

このモジュールはPowerShellコントローラーの設定クラスを提供します。
"""
import os
import sys
import platform
from typing import Dict, Optional, List, Union, Any
from pydantic import BaseModel, Field

class PowerShellControllerSettings(BaseModel):
    """PowerShellコントローラーの設定"""
    
    # インナークラス定義
    class TimeoutSettings(BaseModel):
        """タイムアウト設定"""
        default: float = Field(default=30.0, description="デフォルトのタイムアウト時間（秒）")
        startup: float = Field(default=10.0, description="プロセス起動用のタイムアウト（秒）")
        shutdown: float = Field(default=5.0, description="シャットダウン用のタイムアウト（秒）")
    
    # PowerShellの実行パス
    powershell_executable: str = Field(
        default="powershell" if platform.system().lower() == "windows" else "pwsh",
        description="PowerShellの実行パス"
    )
    
    # タイムアウト設定
    timeout: TimeoutSettings = Field(
        default_factory=TimeoutSettings,
        description="タイムアウト設定"
    )
    
    # エンコーディング
    encoding: str = Field(
        default="utf-8",
        description="PowerShellプロセスとの通信に使用するエンコーディング"
    )
    
    # デバッグモード
    debug: bool = Field(
        default=False,
        description="デバッグモードを有効にするかどうか"
    )
    
    # カスタムホストを使用するかどうか
    use_custom_host: bool = Field(
        default=True,
        description="カスタムホストを使用するかどうか"
    )
    
    # PowerShellコマンドライン引数
    arguments: List[str] = Field(
        default_factory=lambda: [
            "-NoProfile", 
            "-ExecutionPolicy", "Bypass",
            "-NoLogo",
            "-NonInteractive"
        ],
        description="PowerShell実行時の引数"
    )
    
    def get_command_args(self) -> List[str]:
        """
        PowerShellコマンドライン引数を取得します。
        
        Returns:
            List[str]: コマンドライン引数のリスト
        """
        return [self.powershell_executable] + self.arguments 