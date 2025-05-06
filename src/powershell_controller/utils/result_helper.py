"""
Result型を使用したヘルパー関数
"""
from typing import Any, Callable, TypeVar, Generic, Optional, Dict, List, Union, Tuple, cast, overload
from result import Result, Ok, Err
from ..core.errors import PowerShellError, PowerShellExecutionError, PowerShellTimeoutError

T = TypeVar('T')
E = TypeVar('E', bound=Exception)
F = TypeVar('F')  # 関数の戻り値型用の型変数

class ResultHandler(Generic[T, E]):
    """
    Result型の処理を簡易化するヘルパークラス
    
    Example:
        # 成功の場合
        result = ResultHandler.from_function(lambda: "success")
        value = result.unwrap_or("default")  # "success"
        
        # 失敗の場合
        def failing_func():
            raise ValueError("エラー")
            
        result = ResultHandler.from_function(failing_func)
        value = result.unwrap_or("default")  # "default"
    """
    
    @staticmethod
    def from_function(func: Callable[..., F], *args: Any, **kwargs: Any) -> Result[F, PowerShellError]:
        """
        関数をResult型でラップする
        
        Args:
            func: ラップする関数
            *args: 関数に渡す位置引数
            **kwargs: 関数に渡すキーワード引数
            
        Returns:
            Result型
        """
        try:
            return Ok(func(*args, **kwargs))
        except PowerShellError as e:
            return Err(e)
        except Exception as e:
            return Err(PowerShellExecutionError(str(e)))
    
    @staticmethod
    def from_value(value: T) -> Result[T, PowerShellError]:
        """
        値をOk(value)でラップする
        
        Args:
            value: ラップする値
            
        Returns:
            Result型
        """
        return Ok(value)
    
    @staticmethod
    def from_error(error: Union[str, Exception]) -> Result[T, PowerShellError]:
        """
        エラーをErr(error)でラップする
        
        Args:
            error: エラーメッセージまたは例外
            
        Returns:
            Result型
        """
        if isinstance(error, str):
            return Err(PowerShellExecutionError(error))
        elif isinstance(error, PowerShellError):
            return Err(error)
        else:
            return Err(PowerShellExecutionError(str(error)))
    
    @staticmethod
    def combine(results: List[Result[T, E]]) -> Result[List[T], E]:
        """
        複数のResult型を結合する
        すべてOkの場合はOk([values])、1つでもErrの場合は最初のErrを返す
        
        Args:
            results: Result型のリスト
            
        Returns:
            結合したResult型
        """
        values: List[T] = []
        for result in results:
            if result.is_err():
                return cast(Result[List[T], E], result)
            values.append(result.unwrap())
        return Ok(values)
    
    @staticmethod
    def unwrap_or(result: Result[T, E], default: T) -> T:
        """
        Result型から値を取り出す。Errの場合はデフォルト値を返す
        
        Args:
            result: Result型
            default: デフォルト値
            
        Returns:
            取り出した値またはデフォルト値
        """
        if result.is_ok():
            return result.unwrap()
        return default
    
    @staticmethod
    def unwrap_or_else(result: Result[T, E], func: Callable[[E], T]) -> T:
        """
        Result型から値を取り出す。Errの場合は関数を実行して返す
        
        Args:
            result: Result型
            func: エラー値を処理する関数
            
        Returns:
            取り出した値または関数の結果
        """
        if result.is_ok():
            return result.unwrap()
        return func(result.unwrap_err()) 
