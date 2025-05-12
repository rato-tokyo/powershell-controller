#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PowerShellコントローラーの基本的な使用例
"""

from py_pshell.config import PowerShellControllerSettings
from py_pshell.controller import PowerShellController
from py_pshell.errors import PowerShellExecutionError, PowerShellTimeoutError


def basic_example():
    """基本的な使用例"""
    print("===== 基本的な使用例 =====")

    # コントローラー設定（必要に応じてカスタマイズ可能）
    settings = PowerShellControllerSettings(debug=True)  # デバッグモード有効化

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

        # エラーハンドリング例 - 例外処理
        print("\n[3] try-exceptによるエラーハンドリング:")
        try:
            output = controller.execute_command("Get-NonExistentCommand")
            print(f"  出力: {output}")
        except PowerShellExecutionError as e:
            print(f"  実行エラーが発生しました: {e}")
        except PowerShellTimeoutError as e:
            print(f"  タイムアウトが発生しました: {e}")
        except Exception as e:
            print(f"  その他のエラー: {e}")

        # タイムアウト設定の例
        print("\n[4] タイムアウト設定:")
        try:
            # 短いタイムアウトで長時間実行するコマンドを実行
            output = controller.execute_command(
                "Start-Sleep -Seconds 1; Write-Output 'タイムアウト前に完了'", timeout=3.0
            )
            print(f"  出力: {output}")
        except PowerShellTimeoutError as e:
            print(f"  タイムアウトエラー: {e}")

    finally:
        # リソースのクリーンアップ
        controller.close_sync()
        print("\n===== 完了 =====")


if __name__ == "__main__":
    basic_example()
