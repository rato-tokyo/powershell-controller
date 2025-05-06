"""
PowerShellコントローラー非同期パッケージ

PowerShellコントローラーの非同期処理機能を提供します。
"""
from beartype import BeartypeConf
from beartype.claw import beartype_this_package
from typing import Any, Optional, Type, TypeVar, cast

# バージョン情報
__version__ = "0.1.0"

# beartype実行時型チェックをアクティブ化
beartype_conf = BeartypeConf(
    is_debug=True,
    violation_type=Exception,
)
beartype_this_package(conf=beartype_conf)

# APIのエクスポート
from .async_loop import (
    AsyncLoopManager,
    create_task,
    run_in_loop,
    run_as_task,
    get_event_loop
)
from .async_utils import (
    TaskManager,
    Semaphore,
    gather_with_concurrency,
    gather_limit,
    complete_or_cancel,
    timeout_handler
)

# エクスポート
__all__ = [
    # 非同期ループ管理
    "AsyncLoopManager",
    "create_task",
    "run_in_loop",
    "run_as_task",
    "get_event_loop",
    # 非同期ユーティリティ
    "TaskManager",
    "Semaphore",
    "gather_with_concurrency",
    "gather_limit",
    "complete_or_cancel",
    "timeout_handler"
] 