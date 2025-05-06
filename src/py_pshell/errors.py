"""
PowerShellコントローラーのエラークラス定義

このモジュールはPowerShellコントローラーで使用されるすべてのエラークラスを定義します。
"""
from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
from result import Result, Ok, Err

# 型変数
T = TypeVar('T')
E = TypeVar('E', bound=Exception)

class PowerShellError(Exception):
    """PowerShell操作の基本エラークラス"""
    
    def __init__(self, message: str = "PowerShell操作でエラーが発生しました"):
        self.message = message
        super().__init__(self.message)

class PowerShellStartupError(PowerShellError):
    """PowerShellプロセスの起動時エラー"""
    
    def __init__(self, message: str = "PowerShellプロセスの起動に失敗しました"):
        super().__init__(message)

class PowerShellShutdownError(PowerShellError):
    """PowerShellプロセスの終了時エラー"""
    
    def __init__(self, message: str = "PowerShellプロセスの終了に失敗しました"):
        super().__init__(message)

class PowerShellExecutionError(PowerShellError):
    """PowerShellコマンド実行時のエラー"""
    
    def __init__(self, message: str = "PowerShellコマンドの実行に失敗しました", command: Optional[str] = None):
        self.command = command
        if command:
            message = f"{message} (コマンド: {command})"
        super().__init__(message)

class PowerShellTimeoutError(PowerShellError):
    """PowerShell操作のタイムアウトエラー"""
    
    def __init__(self, message: str = "PowerShell操作がタイムアウトしました", operation: Optional[str] = None, timeout: Optional[float] = None):
        self.operation = operation
        self.timeout = timeout
        
        if operation and timeout:
            message = f"{message} (操作: {operation}, タイムアウト: {timeout}秒)"
        elif operation:
            message = f"{message} (操作: {operation})"
        elif timeout:
            message = f"{message} (タイムアウト: {timeout}秒)"
            
        super().__init__(message)

class CommunicationError(PowerShellError):
    """PowerShellプロセスとの通信エラー"""
    
    def __init__(self, message: str = "PowerShellプロセスとの通信に失敗しました"):
        super().__init__(message)

class ProcessError(PowerShellError):
    """PowerShellプロセス操作エラー"""
    
    def __init__(self, message: str = "PowerShellプロセス操作でエラーが発生しました"):
        super().__init__(message)

def as_result(func: Callable[..., T]) -> Callable[..., Result[T, PowerShellError]]:
    """
    関数をResult型を返すように変換するデコレータ
    
    Args:
        func: 変換する関数
        
    Returns:
        Result型を返す関数
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Result[T, PowerShellError]:
        try:
            result = func(*args, **kwargs)
            return Ok(result)
        except PowerShellError as e:
            return Err(e)
        except Exception as e:
            return Err(PowerShellError(str(e)))
    return wrapper 