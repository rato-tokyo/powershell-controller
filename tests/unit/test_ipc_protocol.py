"""
IPCプロトコルのテストケース
"""
import pytest
from py_pshell.infra.ipc.protocol import (
    IPCMessage,
    IPCProtocol,
    MessageType
)
from py_pshell.core.errors import CommunicationError

def test_message_creation():
    """メッセージ作成のテスト"""
    # コマンドメッセージ
    cmd_msg = IPCProtocol.create_command_message(
        "Get-Process",
        id="test-cmd-1"
    )
    assert cmd_msg.type == MessageType.COMMAND
    assert cmd_msg.content == "Get-Process"
    assert cmd_msg.id == "test-cmd-1"
    
    # エラーメッセージ
    error = CommunicationError("Test error", direction="send", data="test data")
    err_msg = IPCProtocol.create_error_message(error)
    assert err_msg.type == MessageType.ERROR
    assert isinstance(err_msg.content, dict)
    assert err_msg.content["type"] == "CommunicationError"
    assert err_msg.content["message"] == "Test error"
    assert err_msg.content["direction"] == "send"
    assert err_msg.content["data"] == "test data"
    
    # システムメッセージ
    sys_msg = IPCProtocol.create_system_message("Session ready")
    assert sys_msg.type == MessageType.SYSTEM
    assert sys_msg.content == "Session ready"

def test_message_serialization():
    """メッセージのシリアライズテスト"""
    original_msg = IPCMessage(
        type=MessageType.COMMAND,
        content="Test command",
        id="test-1"
    )
    
    # 辞書への変換
    dict_data = original_msg.to_dict()
    assert dict_data["type"] == MessageType.COMMAND.value
    assert dict_data["content"] == "Test command"
    assert dict_data["id"] == "test-1"
    
    # シリアライズとデシリアライズ
    serialized = IPCProtocol.serialize(original_msg)
    restored_msg = IPCProtocol.deserialize(serialized)
    assert restored_msg.type == original_msg.type
    assert restored_msg.content == original_msg.content
    assert restored_msg.id == original_msg.id

def test_output_parsing():
    """出力解析のテスト"""
    # JSON形式の出力
    json_output = '{"type": "result", "content": "success", "id": "test-1"}'
    msg = IPCProtocol.parse_output(json_output)
    assert msg is not None
    assert msg.type == MessageType.RESULT
    assert msg.content == "success"
    assert msg.id == "test-1"
    
    # エラーメッセージの出力
    error_output = "ERROR: Test error message"
    msg = IPCProtocol.parse_output(error_output)
    assert msg is not None
    assert msg.type == MessageType.ERROR
    assert isinstance(msg.content, dict)
    assert msg.content["message"] == "Test error message"
    
    # 通常の出力
    normal_output = "Normal output"
    msg = IPCProtocol.parse_output(normal_output)
    assert msg is None

def test_invalid_message_handling():
    """無効なメッセージの処理テスト"""
    # 不正なJSON
    with pytest.raises(CommunicationError) as exc_info:
        IPCProtocol.deserialize("{invalid json}")
    assert "Failed to deserialize message" in str(exc_info.value)
    
    # 必須フィールドの欠落
    with pytest.raises(ValueError) as exc_info:
        IPCMessage.from_dict({"content": "test"})
    assert "Invalid message data" in str(exc_info.value)
    
    # 不正なメッセージタイプ
    with pytest.raises(ValueError) as exc_info:
        IPCMessage.from_dict({
            "type": "invalid_type",
            "content": "test"
        })
    assert "Invalid message data" in str(exc_info.value) 