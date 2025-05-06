"""
エラー定義モジュール
"""
from typing import Any, Dict, Optional, TypeVar, Generic, Union

# result パッケージを使用してエラーハンドリングを改善
from result import Result, Ok, Err

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

# エラータイプの定義
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

# Result型を使用したエラーハンドリングヘルパー関数
def ps_result(func):
    """
    関数をResult型でラップするデコレーター
    
    Args:
        func: ラップする関数
        
    Returns:
        Result型を返す関数
    """
    def wrapper(*args, **kwargs) -> Result[Any, PowerShellError]:
        try:
            return Ok(func(*args, **kwargs))
        except PowerShellError as e:
            return Err(e)
        except Exception as e:
            return Err(PowerShellError(str(e)))
    
    return wrapper

# エラー処理ユーティリティ関数
def handle_ps_error(result: Result[T, E], default_value: Optional[T] = None) -> T:
    """
    Result型のエラーを処理するユーティリティ関数
    
    Args:
        result: 処理するResult型
        default_value: エラー時のデフォルト値
        
    Returns:
        結果またはデフォルト値
    """
    if result.is_ok():
        return result.unwrap()
    return default_value 