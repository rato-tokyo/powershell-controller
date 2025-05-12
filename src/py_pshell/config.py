"""
PowerShellコントローラーの設定クラス

このモジュールはPowerShellコントローラーの設定クラスを提供します。
"""

from pathlib import Path

from pydantic import BaseModel, Field


class PowerShellTimeoutSettings(BaseModel):
    """
    PowerShellのタイムアウト設定

    Attributes:
        startup: 起動時のタイムアウト（秒）
        command: コマンド実行のタイムアウト（秒）
        shutdown: 終了時のタイムアウト（秒）
    """

    startup: float = Field(default=30.0, description="起動タイムアウト（秒）")
    shutdown: float = Field(default=10.0, description="シャットダウンタイムアウト（秒）")
    default: float = Field(default=30.0, description="デフォルトのコマンドタイムアウト（秒）")


class PowerShellControllerSettings(BaseModel):
    """
    PowerShellコントローラーの設定

    Attributes:
        powershell_path: PowerShell実行ファイルのパス
        powershell_args: PowerShellコマンドライン引数
        encoding: 文字エンコーディング
        hide_window: PowerShellウィンドウを非表示にするかどうか
        timeout: タイムアウト設定
    """

    powershell_path: Path = Field(
        default=Path("powershell.exe"), description="PowerShell実行ファイルのパス"
    )
    powershell_args: list[str] = Field(
        default_factory=lambda: [
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
        ],
        description="PowerShellコマンドライン引数",
    )
    encoding: str = Field(default="utf-8", description="文字エンコーディング")
    hide_window: bool = Field(
        default=True, description="PowerShellウィンドウを非表示にするかどうか"
    )
    timeout_settings: PowerShellTimeoutSettings = Field(
        default_factory=PowerShellTimeoutSettings, description="タイムアウト設定"
    )
    max_retries: int = Field(default=3, description="最大リトライ回数")
    retry_delay: float = Field(default=1.0, description="リトライ間隔（秒）")

    # デバッグモード
    debug: bool = Field(default=False, description="デバッグモードを有効にするかどうか")

    # カスタムホストを使用するかどうか
    use_custom_host: bool = Field(default=True, description="カスタムホストを使用するかどうか")

    def get_command_args(self) -> list[str]:
        """
        PowerShellコマンドライン引数を取得します。

        Returns:
            List[str]: コマンドライン引数のリスト
        """
        return [str(self.powershell_path)] + self.powershell_args
