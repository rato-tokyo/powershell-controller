"""
PowerShellセッション管理のテンプレート

このテンプレートは、PowerShellセッションの基本的な機能を提供します。
新しいセッション管理クラスを作成する際の基礎として使用してください。
"""

import types
from typing import Self

# 相対インポートから絶対インポートに変更
from py_pshell.utils import get_powershell_executable


class BaseSessionTemplate:
    """PowerShellセッション管理の基本テンプレート"""

    def __init__(self, timeout: float = 10.0) -> None:
        """
        Args:
            timeout: タイムアウト時間（秒）
        """
        self.timeout = timeout
        self.process = None
        self.powershell_executable = get_powershell_executable()

    async def initialize(self) -> None:
        """セッションを初期化"""
        raise NotImplementedError("Subclass must implement initialize()")

    async def cleanup(self) -> None:
        """セッションをクリーンアップ"""
        raise NotImplementedError("Subclass must implement cleanup()")

    async def execute(self, command: str) -> str:
        """
        コマンドを実行

        Args:
            command: 実行するコマンド

        Returns:
            str: 実行結果
        """
        raise NotImplementedError("Subclass must implement execute()")

    async def __aenter__(self) -> Self:
        """非同期コンテキストマネージャのエントリーポイント"""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """非同期コンテキストマネージャの終了ポイント"""
        await self.cleanup()
