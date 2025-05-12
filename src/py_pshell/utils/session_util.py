"""
PowerShellセッションユーティリティモジュール

PowerShellセッションに必要なユーティリティ関数を提供します。
"""

import platform
import subprocess

# PowerShellの初期化スクリプト
INIT_SCRIPT = """
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # 例外が発生してもエンコーディングは既定値を使用
}

$Host.UI.RawUI.WindowTitle = "PowerShell Controller Session"

# 標準のプロンプトを削除して表示をクリーンに
function prompt {
    return ""
}

# 終了ステータスを示す関数
function global:__SetCommandStatus {
    param([bool]$success)
    if ($success) {
        Write-Output "COMMAND_SUCCESS"
    } else {
        Write-Output "COMMAND_ERROR"
    }
}

# コマンド実行のラッパー関数
function global:__ExecuteCommand {
    param([string]$cmd)
    try {
        # コマンドを実行してパイプラインの最後まで全ての出力を取得
        $result = Invoke-Expression $cmd | Out-String
        Write-Output $result
        __SetCommandStatus $true
    } catch {
        Write-Output "Error: $_"
        __SetCommandStatus $false
    }
}

Write-Output "SESSION_READY"
"""


def get_startup_info() -> subprocess.STARTUPINFO | None:
    """
    プラットフォームに応じたプロセス起動情報を取得します。

    Returns:
        subprocess.STARTUPINFO: Windows環境ではSTARTUPINFO、それ以外ではNone
    """
    startup_info = None
    if platform.system().lower() == "windows":
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = subprocess.SW_HIDE
    return startup_info


def prepare_command_execution(command: str) -> str:
    """
    PowerShellでコマンドを実行するための準備を行います。

    Args:
        command: 実行するコマンド

    Returns:
        str: 実行準備が整ったコマンド
    """
    # コマンドをPowerShellのExecuteCommandラッパー関数で実行
    return f"__ExecuteCommand '{command.replace("'", "''")}'"


def parse_command_result(output_lines: list[str]) -> tuple[bool, str]:
    """
    PowerShellコマンドの実行結果を解析します。

    Args:
        output_lines: コマンド出力の行のリスト

    Returns:
        Tuple[bool, str]: (成功したかどうか, 出力テキスト)
    """
    if not output_lines:
        return True, ""

    # 最後の行はステータスマーカー
    status_line = output_lines[-1].strip() if output_lines else ""
    success = status_line == "COMMAND_SUCCESS"

    # 出力テキスト（ステータスマーカーを除く）
    result_text = "\n".join(output_lines[:-1]) if len(output_lines) > 1 else ""

    return success, result_text
