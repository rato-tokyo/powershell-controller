"""
プロセス間通信のプロトコル定義
"""
from enum import Enum
from typing import Optional, Dict, Any
import json

# マーカー定義
START_MARKER = "JSON_START"
END_MARKER = "JSON_END"
ERROR_MARKER = "ERROR_START"

class MessageType(Enum):
    """メッセージタイプの定義"""
    COMMAND = "command"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"

class IPCMessage:
    """IPC メッセージクラス"""
    
    def __init__(
        self,
        message_type: MessageType,
        content: Any,
        metadata: Optional[Dict] = None
    ):
        """
        Args:
            message_type: メッセージタイプ
            content: メッセージ内容
            metadata: 追加のメタデータ
        """
        self.type = message_type
        self.content = content
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        """メッセージを辞書形式に変換"""
        return {
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata
        }

    def to_json(self) -> str:
        """メッセージをJSON形式に変換"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict) -> 'IPCMessage':
        """辞書からメッセージを生成"""
        return cls(
            message_type=MessageType(data["type"]),
            content=data["content"],
            metadata=data.get("metadata", {})
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'IPCMessage':
        """JSONからメッセージを生成"""
        return cls.from_dict(json.loads(json_str))

class IPCProtocol:
    """IPCプロトコルハンドラー"""
    
    @staticmethod
    def format_message(message: IPCMessage) -> str:
        """
        メッセージをプロトコルフォーマットに変換
        
        Args:
            message: IPCメッセージ
            
        Returns:
            str: フォーマット済みメッセージ
        """
        json_str = message.to_json()
        if message.type == MessageType.ERROR:
            return f"{ERROR_MARKER}\n{json_str}\n{END_MARKER}"
        return f"{START_MARKER}\n{json_str}\n{END_MARKER}"

    @staticmethod
    def parse_output(output: str) -> Optional[IPCMessage]:
        """
        出力からメッセージを解析
        
        Args:
            output: 解析する出力文字列
            
        Returns:
            Optional[IPCMessage]: 解析されたメッセージ、解析失敗時はNone
        """
        # エラーメッセージの解析
        if ERROR_MARKER in output:
            try:
                error_content = output.split(ERROR_MARKER)[1].split(END_MARKER)[0].strip()
                return IPCMessage.from_json(error_content)
            except (IndexError, json.JSONDecodeError):
                return None

        # 通常メッセージの解析
        if START_MARKER in output and END_MARKER in output:
            try:
                content = output.split(START_MARKER)[1].split(END_MARKER)[0].strip()
                return IPCMessage.from_json(content)
            except (IndexError, json.JSONDecodeError):
                return None

        return None

    @staticmethod
    def create_command_message(
        command: str,
        metadata: Optional[Dict] = None
    ) -> IPCMessage:
        """
        コマンドメッセージを作成
        
        Args:
            command: 実行するコマンド
            metadata: 追加のメタデータ
            
        Returns:
            IPCMessage: 作成されたメッセージ
        """
        return IPCMessage(
            message_type=MessageType.COMMAND,
            content=command,
            metadata=metadata
        )

    @staticmethod
    def create_error_message(
        error: Exception,
        metadata: Optional[Dict] = None
    ) -> IPCMessage:
        """
        エラーメッセージを作成
        
        Args:
            error: 発生したエラー
            metadata: 追加のメタデータ
            
        Returns:
            IPCMessage: 作成されたメッセージ
        """
        return IPCMessage(
            message_type=MessageType.ERROR,
            content=str(error),
            metadata=metadata
        ) 