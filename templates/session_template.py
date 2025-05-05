"""
PowerShellセッション管理のテンプレート

このテンプレートは、PowerShellセッションの基本的な機能を提供します。
新しいセッション管理クラスを作成する際の基礎として使用してください。
"""
from typing import Optional, Any, Dict
import asyncio
from ..infra.core.utils.process_manager import AsyncProcessManager
from ..infra.core.utils.test_helper import AsyncTestHelper
from ..infra.core.utils.ipc import IPCProtocol, MessageType
from ..infra.core.utils.errors import ProcessError, CommunicationError

class BaseSessionTemplate:
    """PowerShellセッション管理の基本テンプレート"""
    
    def __init__(self, timeout: float = 10.0):
        """
        Args:
            timeout: タイムアウト時間（秒）
        """
        self.timeout = timeout
        self._process_manager = AsyncProcessManager()
        self._ipc = IPCProtocol()
        
    async def initialize(self) -> None:
        """セッションを初期化"""
        raise NotImplementedError("Subclass must implement initialize()")
        
    async def cleanup(self) -> None:
        """セッションをクリーンアップ"""
        raise NotImplementedError("Subclass must implement cleanup()")
        
    async def execute(self, command: str) -> Any:
        """
        コマンドを実行
        
        Args:
            command: 実行するコマンド
            
        Returns:
            Any: 実行結果
        """
        raise NotImplementedError("Subclass must implement execute()")
        
    async def __aenter__(self):
        """非同期コンテキストマネージャのエントリーポイント"""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャの終了ポイント"""
        await self.cleanup() 