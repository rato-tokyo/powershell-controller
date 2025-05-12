"""
インターフェースモジュール

PowerShellコントローラーで使用するインターフェースを定義します。
"""
from typing import Any, Dict, Optional, Protocol, runtime_checkable
from pydantic import BaseModel


@runtime_checkable
class CommandResultProtocol(Protocol):
    """コマンド結果プロトコル"""

    @property
    def output(self) -> str:
        """コマンドの出力"""
        ...

    @property
    def error(self) -> str:
        """エラーメッセージ"""
        ...

    @property
    def success(self) -> bool:
        """実行の成功/失敗"""
        ...

    @property
    def command(self) -> str:
        """実行されたコマンド"""
        ...

    @property
    def execution_time(self) -> float:
        """実行時間（秒）"""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        ...


class PowerShellControllerSettings(BaseModel):
    """PowerShellコントローラーの設定"""

    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0


@runtime_checkable
class PowerShellControllerProtocol(Protocol):
    """PowerShellコントローラープロトコル"""

    async def __aenter__(self) -> "PowerShellControllerProtocol":
        """非同期コンテキストマネージャーのエントリーポイント"""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """非同期コンテキストマネージャーのエグジットポイント"""
        ...

    async def start(self) -> None:
        """セッションを開始"""
        ...

    async def close(self) -> None:
        """セッションを終了"""
        ...

    def close_sync(self) -> None:
        """セッションを同期的に終了"""
        ...

    async def execute_command(self, command: str, timeout: Optional[float] = None) -> str:
        """コマンドを実行"""
        ...

    async def run_command(self, command: str, timeout: Optional[float] = None) -> CommandResultProtocol:
        """コマンドを実行し、結果を返す"""
        ...

    async def run_script(self, script: str, timeout: Optional[float] = None) -> CommandResultProtocol:
        """スクリプトを実行し、結果を返す"""
        ...

    async def get_json(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """コマンドを実行し、結果をJSONとして返す"""
        ...
