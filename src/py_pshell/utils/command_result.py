"""
コマンド結果モジュール

PowerShellコマンドの実行結果を表すクラスを提供します。
"""
from typing import Dict, Any
from pydantic import BaseModel, Field


class CommandResult(BaseModel):
    """コマンド結果クラス

    PowerShellコマンドの実行結果を表すクラスです。
    """

    output: str = Field(default="", description="コマンドの出力")
    error: str = Field(default="", description="エラーメッセージ")
    success: bool = Field(default=True, description="実行の成功/失敗")
    command: str = Field(..., description="実行されたコマンド")
    execution_time: float = Field(..., description="実行時間（秒）")

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換します。

        Returns:
            Dict[str, Any]: 辞書形式の結果
        """
        return self.model_dump()
