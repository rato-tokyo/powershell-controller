"""
ユーティリティパッケージ

PowerShellコントローラーで使用するユーティリティを提供します。
"""

import os
import platform
import tempfile
from typing import Any, Dict

from .command_executor import CommandExecutor
from .command_result import CommandResult

__all__ = [
    "CommandExecutor",
    "CommandResult",
]


def get_powershell_executable() -> str:
    """
    環境に応じたPowerShell実行ファイルのパスを返します。

    Returns:
        str: PowerShell実行ファイルのパス
    """
    system = platform.system().lower()

    if system == "windows":
        # PowerShell 7 (pwsh.exe)を優先
        pwsh_path = os.path.join(
            os.environ.get("ProgramFiles", r"C:\Program Files"), "PowerShell", "7", "pwsh.exe"
        )
        if os.path.exists(pwsh_path):
            return pwsh_path

        # Windows PowerShell (powershell.exe)
        return r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
    else:
        # Linux/macOS
        return "pwsh"


async def create_temp_script(content: str, prefix: str = "ps_script_", suffix: str = ".ps1") -> str:
    """
    一時的なPowerShellスクリプトファイルを作成します。

    Args:
        content: スクリプトの内容
        prefix: ファイル名の接頭辞
        suffix: ファイル名の接尾辞

    Returns:
        str: 作成されたスクリプトファイルのパス
    """
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, text=True)
    try:
        os.write(fd, content.encode("utf-8"))
    finally:
        os.close(fd)
    return path


def escape_powershell_string(s: str) -> str:
    """
    PowerShellの文字列リテラルの中で使用するために文字列をエスケープします。

    Args:
        s: エスケープする文字列

    Returns:
        str: エスケープされた文字列
    """
    # シングルクォートをエスケープ
    return s.replace("'", "''")


def format_powershell_args(args: Dict[str, Any]) -> str:
    """
    PowerShellコマンドレットのパラメータとして使用するための引数フォーマットを行います。

    Args:
        args: パラメータ名と値の辞書

    Returns:
        str: フォーマットされたパラメータ文字列
    """
    parts = []
    for name, value in args.items():
        # 値の型に基づいて適切な形式にフォーマット
        if value is None:
            continue
        elif isinstance(value, bool):
            if value:
                parts.append(f"-{name}")
            else:
                parts.append(f"-{name}:$false")
        elif isinstance(value, (int, float)):
            parts.append(f"-{name} {value}")
        elif isinstance(value, str):
            parts.append(f"-{name} '{escape_powershell_string(value)}'")
        elif isinstance(value, list):
            values = ",".join(f"'{escape_powershell_string(str(v))}'" for v in value)
            parts.append(f"-{name} @({values})")
        else:
            # その他の型は文字列として扱う
            parts.append(f"-{name} '{escape_powershell_string(str(value))}'")

    return " ".join(parts)
