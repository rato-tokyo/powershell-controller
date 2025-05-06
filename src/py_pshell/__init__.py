"""
PowerShellコントローラーパッケージ

Pythonから簡単にPowerShellを操作するためのライブラリです。
"""

from .controller import PowerShellController, CommandResult
from .interfaces import PowerShellControllerProtocol, CommandResultProtocol
from .config import PowerShellControllerSettings, TimeoutConfig, PowerShellConfig
from .errors import (
    PowerShellError,
    PowerShellExecutionError,
    PowerShellTimeoutError,
    PowerShellStartupError,
    PowerShellShutdownError,
    CommunicationError,
    ProcessError
)

# バージョン情報
__version__ = '1.0.0'
__author__ = 'PowerShell Controller Team'
__all__ = [
    'PowerShellController',
    'CommandResult',
    'PowerShellControllerProtocol',
    'CommandResultProtocol',
    'PowerShellControllerSettings',
    'TimeoutConfig',
    'PowerShellConfig',
    'PowerShellError',
    'PowerShellExecutionError',
    'PowerShellTimeoutError',
    'PowerShellStartupError',
    'PowerShellShutdownError',
    'CommunicationError',
    'ProcessError'
]

# ユーティリティ関数
from . import utils 