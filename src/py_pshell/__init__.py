"""
PowerShellコントローラーパッケージ

Pythonから簡単にPowerShellを操作するためのライブラリです。
"""

from .config import PowerShellControllerSettings
from .controller import PowerShellController
from .errors import (
    CommunicationError,
    PowerShellError,
    PowerShellExecutionError,
    PowerShellShutdownError,
    PowerShellStartupError,
    PowerShellTimeoutError,
    ProcessError,
)
from .interfaces import CommandResultProtocol, PowerShellControllerProtocol
from .utils.command_result import CommandResult

# バージョン情報
__version__ = "1.0.0"
__author__ = "PowerShell Controller Team"
__all__ = [
    "PowerShellController",
    "CommandResult",
    "PowerShellControllerProtocol",
    "CommandResultProtocol",
    "PowerShellControllerSettings",
    "PowerShellError",
    "PowerShellExecutionError",
    "PowerShellTimeoutError",
    "PowerShellStartupError",
    "PowerShellShutdownError",
    "CommunicationError",
    "ProcessError",
]

# ユーティリティ関数
