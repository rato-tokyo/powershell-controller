"""
プロセス間通信のためのプロトコル定義
"""
from typing import Optional, Any, Dict, Union
import json
import enum
from ...core.errors import CommunicationError

class MessageType(enum.Enum):
    """メッセージタイプの定義"""
    COMMAND = "command"
    RESULT = "result"
    ERROR = "error"
    SYSTEM = "system"

class IPCMessage:
    """IPCメッセージを表すクラス"""
    
    def __init__(
        self,
        type: MessageType,
        content: Union[str, Dict[str, Any]],
        id: Optional[str] = None
    ):
        """
        IPCメッセージを初期化します。
        
        Args:
            type: メッセージタイプ
            content: メッセージの内容
            id: メッセージID（オプション）
        """
        self.type = type
        self.content = content
        self.id = id
        
    def to_dict(self) -> Dict[str, Any]:
        """メッセージを辞書形式に変換します。"""
        result: Dict[str, Any] = {
            "type": self.type.value,
            "content": self.content,
        }
        if self.id is not None:
            result["id"] = self.id
        return result
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IPCMessage':
        """
        辞書形式からIPCメッセージを作成します。
        
        Args:
            data: メッセージデータの辞書
            
        Returns:
            IPCMessageインスタンス
            
        Raises:
            ValueError: 無効なメッセージデータの場合
        """
        if "type" not in data or "content" not in data:
            raise ValueError("Invalid message data: missing required fields")
            
        try:
            return cls(
                type=MessageType(data["type"]),
                content=data["content"],
                id=data.get("id")
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Invalid message data: {e}")

class IPCProtocol:
    """IPCプロトコルの実装"""
    
    @staticmethod
    def create_command_message(command: str, id: Optional[str] = None) -> IPCMessage:
        """コマンドメッセージを作成します。"""
        return IPCMessage(
            type=MessageType.COMMAND,
            content=command,
            id=id
        )
        
    @staticmethod
    def create_result_message(result: Any, id: Optional[str] = None) -> IPCMessage:
        """結果メッセージを作成します。"""
        return IPCMessage(
            type=MessageType.RESULT,
            content=result,
            id=id
        )
        
    @staticmethod
    def create_error_message(error: Exception, id: Optional[str] = None) -> IPCMessage:
        """エラーメッセージを作成します。"""
        error_data: Dict[str, Any] = {
            "type": type(error).__name__,
            "message": str(error)
        }
        
        if isinstance(error, CommunicationError):
            if hasattr(error, "direction"):
                error_data["direction"] = error.direction
            if hasattr(error, "data"):
                error_data["data"] = error.data
            
        return IPCMessage(
            type=MessageType.ERROR,
            content=error_data,
            id=id
        )
        
    @staticmethod
    def create_system_message(message: str, id: Optional[str] = None) -> IPCMessage:
        """システムメッセージを作成します。"""
        return IPCMessage(
            type=MessageType.SYSTEM,
            content=message,
            id=id
        )
        
    @staticmethod
    def serialize(message: IPCMessage) -> str:
        """
        メッセージをシリアライズします。
        
        Args:
            message: シリアライズするメッセージ
            
        Returns:
            シリアライズされた文字列
        """
        try:
            return json.dumps(message.to_dict())
        except Exception as e:
            raise CommunicationError(
                "Failed to serialize message",
                direction="send",
                data=str(e)
            )
            
    @staticmethod
    def deserialize(data: str) -> IPCMessage:
        """
        メッセージをデシリアライズします。
        
        Args:
            data: デシリアライズするデータ
            
        Returns:
            IPCMessageインスタンス
            
        Raises:
            CommunicationError: デシリアライズに失敗した場合
        """
        try:
            message_data = json.loads(data)
            return IPCMessage.from_dict(message_data)
        except Exception as e:
            raise CommunicationError(
                "Failed to deserialize message",
                direction="receive",
                data=str(e)
            )
            
    @staticmethod
    def parse_output(output: str) -> Optional[IPCMessage]:
        """
        PowerShellの出力を解析します。
        
        Args:
            output: 解析する出力文字列
            
        Returns:
            IPCMessageインスタンス、または解析できない場合はNone
        """
        try:
            # JSON形式のメッセージを探す
            if output.startswith("{") and output.endswith("}"):
                return IPCProtocol.deserialize(output)
                
            # エラーメッセージを探す
            if output.startswith("ERROR:"):
                error_message = output[6:].strip()
                return IPCProtocol.create_error_message(
                    CommunicationError(
                        error_message,
                        direction="receive"
                    )
                )
                
            # 通常の出力
            return None
            
        except Exception:
            return None 
