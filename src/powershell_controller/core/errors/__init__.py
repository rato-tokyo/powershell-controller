"""
PowerShellコントローラーのエラー定義
"""
from typing import Optional

class PowerShellError(Exception):
    """PowerShellコントローラーの基本エラークラス"""
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message)
        self.details = details

class PowerShellTimeoutError(PowerShellError):
    """タイムアウトエラー"""
    pass

class PowerShellExecutionError(PowerShellError):
    """PowerShellスクリプトの実行エラー"""
    pass

class ProcessError(PowerShellError):
    """プロセス管理に関するエラー"""
    pass

class CommunicationError(PowerShellError):
    """プロセス間通信に関するエラー"""
    def __init__(self, message: str, direction: str, data: Optional[str] = None):
        super().__init__(message)
        self.direction = direction  # "send" or "receive"
        self.data = data

__all__ = [
    'PowerShellError',
    'PowerShellTimeoutError',
    'PowerShellExecutionError',
    'ProcessError',
    'CommunicationError',
] 