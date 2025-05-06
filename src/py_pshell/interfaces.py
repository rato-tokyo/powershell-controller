"""
PowerShellコントローラーインターフェース

PowerShellを操作するためのインターフェース定義を提供します。
テストやモック作成を容易にするためのプロトコル定義です。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from result import Result

from .errors import PowerShellError

class CommandResultProtocol(ABC):
    """
    PowerShellコマンド実行結果のプロトコル
    """
    @property
    @abstractmethod
    def output(self) -> str:
        """コマンドの標準出力"""
        pass
        
    @property
    @abstractmethod
    def error(self) -> str:
        """コマンドの標準エラー出力"""
        pass
        
    @property
    @abstractmethod
    def success(self) -> bool:
        """コマンドが成功したかどうか"""
        pass
        
    @property
    @abstractmethod
    def command(self) -> str:
        """実行されたコマンド"""
        pass
        
    @property
    @abstractmethod
    def execution_time(self) -> float:
        """実行時間（秒）"""
        pass
        
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式で結果を返す"""
        pass

class PowerShellControllerProtocol(ABC):
    """
    PowerShellコントローラーのプロトコル
    
    PowerShellコマンドを実行するためのインターフェースを定義します。
    テストやモックの作成を容易にするための抽象クラスです。
    """
    
    @abstractmethod
    async def run_command(self, command: str, timeout: Optional[float] = None) -> CommandResultProtocol:
        """
        PowerShellコマンドを非同期で実行します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            CommandResultProtocol: コマンドの実行結果
        """
        pass
    
    @abstractmethod
    async def run_script(self, script: str, timeout: Optional[float] = None) -> CommandResultProtocol:
        """
        PowerShellスクリプトを非同期で実行します。
        
        Args:
            script: 実行するPowerShellスクリプト
            timeout: スクリプト実行のタイムアウト（秒）
            
        Returns:
            CommandResultProtocol: スクリプトの実行結果
        """
        pass
    
    @abstractmethod
    def execute_command(self, command: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellコマンドを同期的に実行します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            str: コマンドの実行結果
        """
        pass
    
    @abstractmethod
    def execute_command_result(self, command: str, timeout: Optional[float] = None) -> Result[str, PowerShellError]:
        """
        PowerShellコマンドを実行し、Result型で結果を返します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            Result[str, PowerShellError]: 成功した場合はOk(output)、失敗した場合はErr(error)
        """
        pass
    
    @abstractmethod
    def execute_script(self, script: str, timeout: Optional[float] = None) -> str:
        """
        PowerShellスクリプトを実行します。
        
        Args:
            script: 実行するPowerShellスクリプト
            timeout: スクリプト実行のタイムアウト（秒）
            
        Returns:
            str: スクリプトの実行結果
        """
        pass
    
    @abstractmethod
    def execute_script_result(self, script: str, timeout: Optional[float] = None) -> Result[str, PowerShellError]:
        """
        PowerShellスクリプトを実行し、Result型で結果を返します。
        
        Args:
            script: 実行するPowerShellスクリプト
            timeout: スクリプト実行のタイムアウト（秒）
            
        Returns:
            Result[str, PowerShellError]: 成功した場合はOk(output)、失敗した場合はErr(error)
        """
        pass
    
    @abstractmethod
    def get_json(self, command: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        PowerShellコマンドを実行し、結果をJSON形式で解析して返します。
        
        Args:
            command: 実行するPowerShellコマンド
            timeout: コマンド実行のタイムアウト（秒）
            
        Returns:
            Dict[str, Any]: JSONデータを解析した辞書
        """
        pass
    
    @abstractmethod
    def get_environment_variable(self, name: str) -> str:
        """
        PowerShell環境変数の値を取得します。
        
        Args:
            name: 環境変数名
            
        Returns:
            str: 環境変数の値
        """
        pass
    
    @abstractmethod
    def set_environment_variable(self, name: str, value: str) -> None:
        """
        PowerShell環境変数を設定します。
        
        Args:
            name: 環境変数名
            value: 設定する値
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        PowerShellセッションを閉じます。
        """
        pass
    
    @abstractmethod
    def close_sync(self) -> None:
        """
        PowerShellセッションを同期的に閉じます。
        """
        pass 