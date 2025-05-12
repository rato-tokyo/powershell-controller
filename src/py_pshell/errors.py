"""
PowerShellコントローラーのエラークラス定義

このモジュールはPowerShellコントローラーで使用されるすべてのエラークラスを定義します。
"""

from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from result import Err, Ok, Result

# 型変数
T = TypeVar("T")
E = TypeVar("E", bound=Exception)


class PowerShellError(Exception):
    """PowerShellエラーの基底クラス"""



class PowerShellStartupError(PowerShellError):
    """セッション開始エラー"""



class PowerShellShutdownError(PowerShellError):
    """セッション終了エラー"""



class PowerShellExecutionError(PowerShellError):
    """コマンド実行エラー"""



class PowerShellTimeoutError(PowerShellError):
    """PowerShellコマンドの実行がタイムアウトした場合の例外"""

    def __init__(
        self,
        message: str = "PowerShell操作がタイムアウトしました",
        operation: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
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


class PowerShellStreamError(PowerShellError):
    """PowerShellストリームの操作に失敗した場合の例外"""

    def __init__(self, message: str = "PowerShellストリームの操作に失敗しました"):
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
