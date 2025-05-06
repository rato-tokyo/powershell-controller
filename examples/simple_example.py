#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PowerShellコントローラーの基本的な使用例
"""

from py_pshell.controller import PowerShellController
from py_pshell.config import PowerShellControllerSettings
from py_pshell.errors import PowerShellExecutionError

def basic_example():
    """基本的な使用例"""
    print("===== 基本的な使用例 =====")
    
    # モックモードを使用（実際のPowerShellを使用する場合はFalseに設定）
    settings = PowerShellControllerSettings(use_mock=True)
    
    # コントローラーの初期化
    controller = PowerShellController(settings=settings)
    
    try:
        # 基本的なコマンド実行
        print("\n[1] 基本的なコマンド実行:")
        output = controller.execute_command("Write-Output 'Hello from PowerShell'")
        print(f"  出力: {output}")
        
        # PowerShellスクリプトの実行
        print("\n[2] スクリプトの実行:")
        script = """
        $numbers = 1..5
        $sum = ($numbers | Measure-Object -Sum).Sum
        Write-Output "合計: $sum"
        """
        output = controller.execute_command(script)
        print(f"  出力: {output}")
        
        # エラーハンドリング例
        print("\n[3] エラーハンドリング:")
        try:
            output = controller.execute_command("Get-NonExistentCommand")
        except PowerShellExecutionError as e:
            print(f"  エラーが発生しました: {e}")
        
        # Result型を使用したエラーハンドリング
        print("\n[4] Result型の使用:")
        result = controller.execute_command_result("Get-Process | Select-Object -First 3")
        if result.is_ok():
            print(f"  成功: {result.unwrap()}")
        else:
            print(f"  エラー: {result.unwrap_err()}")
        
    finally:
        # リソースのクリーンアップ
        controller.close_sync()
        print("\n===== 完了 =====")

if __name__ == "__main__":
    basic_example() 