"""
エラー処理を集約するモジュール

このモジュールはエラー処理を一元管理するためのクラスと関数を提供します。
"""
from typing import Any, Dict, Optional, TypeVar, Callable, Type, Union
import traceback
from loguru import logger
from result import Result, Ok, Err

from .core.errors import (
    PowerShellError,
    PowerShellExecutionError,
    PowerShellTimeoutError,
    ProcessError,
    CommunicationError
)

T = TypeVar('T')

class ErrorHandler:
    """
    エラー処理を集約するクラス
    
    このクラスはエラーのキャプチャ、変換、ロギング、リカバリーを一元管理します。
    """
    
    @staticmethod
    def handle_execution_error(
        error: Exception,
        command: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> PowerShellError:
        """
        コマンド実行時のエラーを処理します。
        
        Args:
            error: 発生したエラー
            command: 実行していたコマンド（あれば）
            context: 追加のコンテキスト情報（あれば）
            
        Returns:
            適切なPowerShellErrorサブクラスのインスタンス
        """
        # コンテキスト情報の初期化
        ctx = context or {}
        if command:
            ctx["command"] = command
            
        # エラータイプとメッセージの設定
        error_type = "unknown"
        error_msg = str(error)
        
        # 既にPowerShellErrorの場合はそのまま返す
        if isinstance(error, PowerShellError):
            logger.error(
                f"PowerShellエラー発生", 
                error_type=type(error).__name__,
                error=error_msg,
                **ctx
            )
            return error
            
        # エラータイプに基づいて変換
        if "timeout" in error_msg.lower():
            error_type = "timeout"
            converted_error = PowerShellTimeoutError(
                f"コマンド実行がタイムアウトしました: {error_msg}",
                details=traceback.format_exc()
            )
        elif any(s in error_msg.lower() for s in ["process", "pipe", "connection"]):
            error_type = "process"
            converted_error = ProcessError(
                f"プロセス関連のエラーが発生しました: {error_msg}",
                details=traceback.format_exc()
            )
        elif any(s in error_msg.lower() for s in ["communication", "protocol", "ipc"]):
            error_type = "communication"
            converted_error = CommunicationError(
                f"通信エラーが発生しました: {error_msg}",
                details=traceback.format_exc()
            )
        else:
            # デフォルトは実行エラー
            error_type = "execution"
            converted_error = PowerShellExecutionError(
                f"コマンド実行エラー: {error_msg}",
                details=traceback.format_exc(),
                cause=error
            )
            
        # エラーをログに記録
        logger.error(
            f"エラーが発生しました",
            error_type=error_type,
            error=error_msg,
            **ctx
        )
        
        return converted_error
    
    @staticmethod
    def capture_and_convert(
        func: Callable[..., T],
        error_context: Optional[Dict[str, Any]] = None
    ) -> Callable[..., Result[T, PowerShellError]]:
        """
        関数を実行し、発生したエラーをキャプチャしてResult型で返すデコレータ関数
        
        Args:
            func: デコレートする関数
            error_context: エラー発生時に含めるコンテキスト情報
            
        Returns:
            Result型を返すラップ関数
        """
        def wrapper(*args, **kwargs):
            try:
                return Ok(func(*args, **kwargs))
            except Exception as e:
                context = error_context or {}
                context["function"] = func.__name__
                error = ErrorHandler.handle_execution_error(e, context=context)
                return Err(error)
        return wrapper
    
    @staticmethod
    def suppress_errors(
        func: Callable[..., T],
        default_value: T,
        log_level: str = "ERROR"
    ) -> Callable[..., T]:
        """
        関数を実行し、エラーが発生した場合はデフォルト値を返すデコレータ関数
        
        Args:
            func: デコレートする関数
            default_value: エラー発生時に返すデフォルト値
            log_level: エラー発生時のログレベル ("ERROR", "WARNING", "INFO")
            
        Returns:
            元の戻り値かデフォルト値を返すラップ関数
        """
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # ログレベルに応じてログ出力
                if log_level == "ERROR":
                    logger.error(f"エラーを抑制しました: {e} - デフォルト値を返します")
                elif log_level == "WARNING":
                    logger.warning(f"エラーを抑制しました: {e} - デフォルト値を返します")
                else:
                    logger.info(f"エラーを抑制しました: {e} - デフォルト値を返します")
                return default_value
        return wrapper
    
    @staticmethod
    def create_error(
        error_type: Union[str, Type[PowerShellError]] = "execution",
        message: str = "",
        details: Optional[str] = None,
        cause: Optional[Exception] = None
    ) -> PowerShellError:
        """
        指定された型のPowerShellErrorを作成します。
        
        Args:
            error_type: エラーの種類かPowerShellErrorのサブクラス
            message: エラーメッセージ
            details: 詳細情報
            cause: 原因となった例外
            
        Returns:
            作成されたPowerShellErrorインスタンス
        """
        if isinstance(error_type, type) and issubclass(error_type, PowerShellError):
            return error_type(message, details=details, cause=cause)
            
        # 文字列の場合、対応するエラータイプを作成
        if error_type == "timeout":
            return PowerShellTimeoutError(message, details=details, cause=cause)
        elif error_type == "process":
            return ProcessError(message, details=details, cause=cause)
        elif error_type == "communication":
            return CommunicationError(message, details=details, cause=cause)
        else:
            # デフォルトは実行エラー
            return PowerShellExecutionError(message, details=details, cause=cause) 