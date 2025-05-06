"""
エラー定義モジュール
"""
from typing import Optional, Any

class PowerShellError(Exception):
    """PowerShell関連のエラーの基底クラス"""
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)

class PowerShellTimeoutError(PowerShellError):
    """PowerShellコマンドのタイムアウト時に発生するエラー"""
    pass

class PowerShellExecutionError(PowerShellError):
    """PowerShellコマンドの実行時に発生するエラー"""
    pass

class ProcessError(PowerShellError):
    """プロセス関連のエラー"""
    pass

class CommunicationError(PowerShellError):
    """通信エラー"""
    def __init__(self, message: str, direction: str = "", data: Any = None):
        self.direction = direction
        self.data = data
        super().__init__(message) 