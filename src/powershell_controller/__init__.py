"""
PowerShell Controller package
"""
import logging
import sys
from loguru import logger

# APIの公開
from .utils.config import PowerShellControllerSettings
from .core.errors import (
    PowerShellError,
    PowerShellTimeoutError,
    PowerShellExecutionError,
    ProcessError,
    CommunicationError
)

# バージョン情報
__version__ = "0.1.0"

# 古いロガーの設定をクリア
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s (%(filename)s:%(lineno)s)",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# loguruの設定
logger.remove()  # デフォルト設定を削除
logger.configure(
    handlers=[
        {
            "sink": sys.stderr, 
            "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            "colorize": True,
            "level": "INFO"
        }
    ]
)

# エクスポート
__all__ = [
    "PowerShellControllerSettings",
    "PowerShellError",
    "PowerShellTimeoutError",
    "PowerShellExecutionError",
    "ProcessError",
    "CommunicationError",
    "logger"
] 