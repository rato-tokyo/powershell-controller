#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PowerShellコントローラーのショートカットメソッド使用例
"""

from py_pshell.controller import PowerShellController
from py_pshell.config import PowerShellControllerSettings

def shortcuts_example():
    """ショートカットメソッドの使用例"""
    print("===== ショートカットメソッドの使用例 =====")
    
    # モックモードで初期化（実際のPowerShellを使用する場合はFalseに設定）
    settings = PowerShellControllerSettings(use_mock=True)
    controller = PowerShellController(settings=settings)
    
    try:
        # JSON取得
        print("\n[1] JSONデータの取得:")
        try:
            data = controller.get_json("Get-Process | Select-Object -First 3 -Property Name,Id,CPU | ConvertTo-Json")
            print(f"  取得データ: {data}")
            
            # モックモードでは実際のJSONは返らないので、模擬データで処理例を示す
            mock_data = [
                {"Name": "chrome", "Id": 1234, "CPU": 10.5},
                {"Name": "explorer", "Id": 2345, "CPU": 5.2},
                {"Name": "pwsh", "Id": 3456, "CPU": 2.1}
            ]
            
            print("  データ処理例:")
            for process in mock_data:
                print(f"    プロセス: {process['Name']}, ID: {process['Id']}, CPU: {process['CPU']}%")
        except Exception as e:
            print(f"  エラー: {e}")
        
        # 環境変数操作
        print("\n[2] 環境変数の操作:")
        controller.set_environment_variable("PS_TEST_VAR", "テスト値")
        value = controller.get_environment_variable("PS_TEST_VAR")
        print(f"  設定した環境変数の値: {value}")
        
        # スクリプト実行
        print("\n[3] スクリプト実行:")
        script = """
        # テストデータの準備
        $users = @(
            @{Name="user1"; Age=25; Active=$true},
            @{Name="user2"; Age=34; Active=$false},
            @{Name="user3"; Age=28; Active=$true}
        )
        
        # フィルタリングと整形
        $active_users = $users | Where-Object { $_.Active -eq $true }
        $result = $active_users | ForEach-Object { "ユーザー: $($_.Name), 年齢: $($_.Age)" }
        $result
        """
        output = controller.execute_script(script)
        print(f"  実行結果: {output}")
        
    finally:
        controller.close_sync()
        print("\n===== 完了 =====")

if __name__ == "__main__":
    shortcuts_example() 