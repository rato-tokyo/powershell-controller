"""
インターフェースモジュール

PowerShellコントローラーで使用するインターフェースを定義します。
"""

import types
from typing import Any, Protocol, runtime_checkable

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

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        ...


@runtime_checkable
class SessionProtocol(Protocol):
    """PowerShellセッションプロトコル"""

    async def execute(self, command: str, timeout: float | None = None) -> str:
        """コマンドを実行"""
        ...

    async def stop(self) -> None:
        """セッションを停止"""
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

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
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

    async def execute_command(self, command: str, timeout: float | None = None) -> str:
        """コマンドを実行"""
        ...

    async def run_command(
        self, command: str, timeout: float | None = None
    ) -> CommandResultProtocol:
        """コマンドを実行し、結果を返す"""
        ...

    async def run_script(self, script: str, timeout: float | None = None) -> CommandResultProtocol:
        """スクリプトを実行し、結果を返す"""
        ...

    async def get_json(self, command: str, timeout: float | None = None) -> dict[str, Any]:
        """コマンドを実行し、結果をJSONとして返す"""
        ...
