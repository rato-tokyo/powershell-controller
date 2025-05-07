"""
PowerShell JSON処理モジュール

PowerShellコマンドの結果をJSONとして処理する機能を提供します。
"""
import json
from typing import Dict, Any, Optional
from loguru import logger

from .errors import PowerShellError, PowerShellExecutionError

class JsonHandler:
    """
    PowerShell JSON処理クラス
    
    PowerShellコマンドの結果をJSONとして処理する機能を提供します。
    """
    
    @staticmethod
    def get_json(command: str, output: str) -> Dict[str, Any]:
        """
        PowerShellコマンドの結果をJSON形式で解析して返します。
        
        Args:
            command: 実行されたコマンド
            output: コマンドの出力
            
        Returns:
            Dict[str, Any]: JSONデータを解析した辞書
            
        Raises:
            ValueError: JSONの解析に失敗した場合
        """
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSONの解析に失敗しました: {e}\n元データ: {output}")
    
    @staticmethod
    def ensure_json_command(command: str) -> str:
        """
        コマンドにConvertTo-Jsonを追加します。
        
        Args:
            command: 元のコマンド
            
        Returns:
            str: ConvertTo-Jsonを追加したコマンド
        """
        if "ConvertTo-Json" not in command:
            return f"{command} | ConvertTo-Json -Depth 10"
        return command 