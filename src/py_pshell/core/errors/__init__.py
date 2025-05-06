"""
PowerShellコントローラーのエラー定義
"""
from typing import Optional, Any, TypeVar, Union
import inspect
import functools
import traceback
from result import Result, Ok, Err

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

class PowerShellError(Exception):
    """PowerShellコントローラーの基本エラークラス"""
    def __init__(self, message: str, details: Optional[str] = None, cause: Optional[Exception] = None):
        self.message = message
        self.details = details
        self.cause = cause
        super_message = f"{message}"
        if details:
            super_message += f" - 詳細: {details}"
        if cause:
            super_message += f" - 原因: {cause}"
        super().__init__(super_message)
        
    def __str__(self) -> str:
        result = self.message
        if self.details:
            result += f" - 詳細: {self.details}"
        if self.cause:
            result += f" - 原因: {str(self.cause)}"
        return result
    
    @classmethod
    def from_exception(cls, exc: Exception, message: Optional[str] = None) -> 'PowerShellError':
        """
        任意の例外からPowerShellErrorを作成します。
        
        Args:
            exc: 元の例外
            message: エラーメッセージ（Noneの場合は元の例外のメッセージを使用）
            
        Returns:
            新しいPowerShellError
        """
        if isinstance(exc, PowerShellError):
            return exc
            
        msg = message or str(exc)
        details = traceback.format_exc()
        return cls(msg, details=details, cause=exc)

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
    def __init__(self, message: str, direction: str = "", data: Any = None, **kwargs):
        self.direction = direction  # "send" or "receive"
        self.data = data
        super().__init__(message, **kwargs)

class ConfigurationError(PowerShellError):
    """設定関連のエラー"""
    pass

class SessionError(PowerShellError):
    """セッション管理関連のエラー"""
    pass

# デコレータ関数
def as_result(func):
    """
    関数の戻り値をResult型にラップするデコレータ
    
    Args:
        func: デコレートする関数
    
    Returns:
        Result型を返すラップ関数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return Ok(func(*args, **kwargs))
        except PowerShellError as e:
            return Err(e)
        except Exception as e:
            # 一般的な例外をPowerShellErrorに変換
            module_name = inspect.getmodule(func).__name__ if inspect.getmodule(func) else "unknown"
            func_name = func.__name__ if hasattr(func, "__name__") else "unknown"
            error = PowerShellError.from_exception(
                e, 
                f"関数 {module_name}.{func_name} の実行中にエラーが発生しました"
            )
            return Err(error)
    return wrapper

def as_async_result(func):
    """
    非同期関数の戻り値をResult型にラップするデコレータ
    
    Args:
        func: デコレートする非同期関数
    
    Returns:
        Result型を返すラップ関数
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            return Ok(result)
        except PowerShellError as e:
            return Err(e)
        except Exception as e:
            # 一般的な例外をPowerShellErrorに変換
            module_name = inspect.getmodule(func).__name__ if inspect.getmodule(func) else "unknown"
            func_name = func.__name__ if hasattr(func, "__name__") else "unknown"
            error = PowerShellError.from_exception(
                e, 
                f"非同期関数 {module_name}.{func_name} の実行中にエラーが発生しました"
            )
            return Err(error)
    return wrapper

__all__ = [
    'PowerShellError',
    'PowerShellTimeoutError',
    'PowerShellExecutionError',
    'ProcessError',
    'CommunicationError',
    'ConfigurationError',
    'SessionError',
    'as_result',
    'as_async_result',
] 