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
    
    # コントローラー初期化
    settings = PowerShellControllerSettings(
        debug=True  # デバッグモード有効化
    )
    controller = PowerShellController(settings=settings)
    
    try:
        # JSON取得
        print("\n[1] JSONデータの取得:")
        try:
            data = controller.get_json("Get-Process | Select-Object -First 3 -Property Name,Id,CPU | ConvertTo-Json")
            print(f"  取得データ: {data}")
            
            # データ処理例
            print("  データ処理例:")
            for process in data:
                name = process.get('Name', 'Unknown')
                process_id = process.get('Id', 0)
                cpu = process.get('CPU', 0)
                print(f"    プロセス: {name}, ID: {process_id}, CPU: {cpu}%")
        except Exception as e:
            print(f"  エラー: {e}")
        
        # スクリプト実行
        print("\n[2] スクリプト実行:")
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