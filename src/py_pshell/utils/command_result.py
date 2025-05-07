"""
PowerShellコマンド実行結果モジュール

PowerShellコマンドの実行結果を表すクラスを提供します。
"""
from typing import Dict, Any

from ..interfaces import CommandResultProtocol

class CommandResult(CommandResultProtocol):
    """
    PowerShellコマンドの実行結果
    
    Attributes:
        output: コマンドの標準出力
        error: コマンドの標準エラー出力
        success: コマンドが成功したかどうか
        command: 実行されたコマンド
        execution_time: 実行時間（秒）
    """
    def __init__(
        self, 
        output: str = "", 
        error: str = "", 
        success: bool = True, 
        command: str = "", 
        execution_time: float = 0.0
    ):
        self._output = output
        self._error = error
        self._success = success
        self._command = command
        self._execution_time = execution_time
    
    def __str__(self) -> str:
        """文字列表現を返します"""
        if self._success:
            return self._output
        return f"エラー: {self._error}"
    
    def __bool__(self) -> bool:
        """ブール値変換（成功したかどうか）"""
        return self._success
    
    @property
    def output(self) -> str:
        """コマンドの標準出力"""
        return self._output
        
    @property
    def error(self) -> str:
        """コマンドの標準エラー出力"""
        return self._error
        
    @property
    def success(self) -> bool:
        """コマンドが成功したかどうか"""
        return self._success
        
    @property
    def command(self) -> str:
        """実行されたコマンド"""
        return self._command
        
    @property
    def execution_time(self) -> float:
        """実行時間（秒）"""
        return self._execution_time
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で結果を返します"""
        return {
            "output": self._output,
            "error": self._error,
            "success": self._success,
            "command": self._command,
            "execution_time": self._execution_time
        } 