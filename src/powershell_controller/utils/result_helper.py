"""
Result型を使用したエラーハンドリングのヘルパークラス
"""
import inspect
import functools
from typing import Any, TypeVar, Callable, Generic, Optional, Dict, List, Union, Type
import traceback
from loguru import logger
from result import Result, Ok, Err

from ..core.errors import PowerShellError

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

class ResultHandler:
    """
    Result型を使用したエラーハンドリングのためのヘルパークラス
    エラーハンドリングを一貫性ある方法で処理します。
    """
    
    @staticmethod
    def from_function(func: Callable[..., T], *args, **kwargs) -> Result[T, PowerShellError]:
        """
        関数をResult型でラップします。
        
        Args:
            func: ラップする関数
            *args: 関数の引数
            **kwargs: 関数のキーワード引数
            
        Returns:
            Result型
        """
        logger.debug(f"Executing function {func.__name__} with Result wrapper")
        try:
            return Ok(func(*args, **kwargs))
        except PowerShellError as e:
            logger.debug(f"PowerShell error caught in ResultHandler: {e}")
            return Err(e)
        except Exception as e:
            # 一般的な例外をPowerShellErrorに変換
            module_name = inspect.getmodule(func).__name__ if inspect.getmodule(func) else "unknown"
            func_name = func.__name__ if hasattr(func, "__name__") else "unknown"
            logger.debug(f"General exception caught in ResultHandler: {e}")
            
            # トレースバックを取得
            error_details = traceback.format_exc()
            
            # PowerShellErrorに変換
            ps_error = PowerShellError(
                f"関数 {module_name}.{func_name} の実行中にエラーが発生しました", 
                details=error_details,
                cause=e
            )
            return Err(ps_error)
    
    @staticmethod
    def from_async_function(async_func: Callable[..., Any], *args, **kwargs) -> Result[Any, PowerShellError]:
        """
        非同期関数をResult型でラップします。
        
        Args:
            async_func: ラップする非同期関数
            *args: 関数の引数
            **kwargs: 関数のキーワード引数
            
        Returns:
            Result型
        """
        import asyncio
        
        logger.debug(f"Executing async function {async_func.__name__} with Result wrapper")
        try:
            # イベントループを取得
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # イベントループがない場合は新しく作成
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            result = loop.run_until_complete(async_func(*args, **kwargs))
            return Ok(result)
        except PowerShellError as e:
            logger.debug(f"PowerShell error caught in async ResultHandler: {e}")
            return Err(e)
        except Exception as e:
            # 一般的な例外をPowerShellErrorに変換
            module_name = inspect.getmodule(async_func).__name__ if inspect.getmodule(async_func) else "unknown"
            func_name = async_func.__name__ if hasattr(async_func, "__name__") else "unknown"
            logger.debug(f"General exception caught in async ResultHandler: {e}")
            
            # トレースバックを取得
            error_details = traceback.format_exc()
            
            # PowerShellErrorに変換
            ps_error = PowerShellError(
                f"非同期関数 {module_name}.{func_name} の実行中にエラーが発生しました", 
                details=error_details,
                cause=e
            )
            return Err(ps_error)
    
    @staticmethod
    def handle_error(result: Result[T, E], default_value: Optional[T] = None) -> T:
        """
        Result型の結果を処理し、エラーの場合はデフォルト値を返します。
        
        Args:
            result: 処理するResult型
            default_value: エラー時のデフォルト値
            
        Returns:
            Okならその値、Errならデフォルト値
        """
        if result.is_ok():
            return result.unwrap()
        logger.debug(f"Error handled with default value: {result.unwrap_err()}")
        return default_value
    
    @staticmethod
    def unwrap_or_log(result: Result[T, E], logger_instance: Optional[logger] = None) -> Optional[T]:
        """
        Result型の結果を取り出し、エラーの場合はログに記録してNoneを返します。
        
        Args:
            result: 処理するResult型
            logger_instance: 使用するロガー（Noneの場合はデフォルトのロガーを使用）
            
        Returns:
            Okならその値、ErrならNone
        """
        log = logger_instance or logger
        
        if result.is_ok():
            return result.unwrap()
        
        error = result.unwrap_err()
        log.error(f"Error unwrapping result: {error}")
        return None
    
    @staticmethod
    def chain_results(results: List[Result[T, E]]) -> Result[List[T], E]:
        """
        複数のResult型を1つのリスト結果にチェーンします。
        すべてがOkならばOk(値のリスト)を返し、1つでもErrがあればErrを返します。
        
        Args:
            results: Result型のリスト
            
        Returns:
            チェーンされたResult型
        """
        values = []
        for result in results:
            if result.is_err():
                return Err(result.unwrap_err())
            values.append(result.unwrap())
        return Ok(values)

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
        return ResultHandler.from_function(func, *args, **kwargs)
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
            
            # トレースバックを取得
            error_details = traceback.format_exc()
            
            # PowerShellErrorに変換
            ps_error = PowerShellError(
                f"非同期関数 {module_name}.{func_name} の実行中にエラーが発生しました", 
                details=error_details,
                cause=e
            )
            return Err(ps_error)
    return wrapper 
