"""
プロセス間通信のためのパッケージ
"""
from .protocol import IPCMessage, IPCProtocol, MessageType

__all__ = [
    'IPCMessage',
    'IPCProtocol',
    'MessageType',
] 