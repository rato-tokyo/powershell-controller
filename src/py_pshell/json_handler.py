"""
PowerShell JSON処理モジュール

PowerShellコマンドの結果をJSONとして処理する機能を提供します。
"""

import json
from typing import Any, cast


class JsonHandler:
    """
    PowerShell JSON処理クラス

    PowerShellコマンドの結果をJSONとして処理する機能を提供します。
    """

    @staticmethod
    def get_json(command: str, output: str) -> dict[str, Any]:
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
            raise ValueError(f"JSONの解析に失敗しました: {e}\n元データ: {output}") from e

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

    @staticmethod
    def parse_json(command: str, output: str) -> dict[str, Any]:
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
            result = json.loads(output)
            if not isinstance(result, dict):
                raise ValueError(f"JSONの解析結果が辞書ではありません: {result}")
            return cast(dict[str, Any], result)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSONの解析に失敗しました: {e}\n元データ: {output}") from e
