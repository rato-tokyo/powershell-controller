"""
PowerShellコントローラーユーティリティパッケージ

PowerShellコントローラーのユーティリティ機能を提供します。
"""
from beartype import BeartypeConf
from beartype.claw import beartype_this_package

# バージョン情報
__version__ = "0.1.0"

# beartype実行時型チェックをアクティブ化
beartype_conf = BeartypeConf(
    is_debug=True,
    violation_type=Exception,
)
beartype_this_package(conf=beartype_conf)

# APIのエクスポート
from .config import (
    PowerShellControllerSettings,
    RetryConfig,
    TimeoutConfig,
    PowerShellConfig,
    LoggingConfig
)
from .result_helper import (
    ResultHandler,
    as_result,
    as_async_result
)
from .errors import (
    PowerShellError,
    PowerShellTimeoutError,
    PowerShellExecutionError,
    ProcessError,
    CommunicationError,
    ConfigurationError,
    SessionError
)

# エクスポート
__all__ = [
    # 設定
    "PowerShellControllerSettings",
    "RetryConfig",
    "TimeoutConfig",
    "PowerShellConfig",
    "LoggingConfig",
    # ヘルパー
    "ResultHandler",
    "as_result",
    "as_async_result",
    # エラー
    "PowerShellError",
    "PowerShellTimeoutError",
    "PowerShellExecutionError",
    "ProcessError",
    "CommunicationError",
    "ConfigurationError",
    "SessionError"
] 