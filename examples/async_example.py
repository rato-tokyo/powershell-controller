#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PowerShellコントローラーの非同期APIの使用例
"""

import asyncio
from py_pshell.controller import PowerShellController
from py_pshell.config import PowerShellControllerSettings

async def async_example():
    """非同期APIの使用例"""
    print("===== 非同期APIの使用例 =====")
    
    # 設定（モックモードはオプション）
    settings = PowerShellControllerSettings(use_mock=True)
    
    # 非同期コンテキストマネージャーとして使用
    async with PowerShellController(settings=settings) as controller:
        # コマンド実行
        print("\n[1] 基本的なコマンド実行:")
        result = await controller.run_command("Write-Output 'Hello from async PowerShell'")
        print(f"  成功: {result.success}")
        print(f"  出力: {result.output}")
        print(f"  実行時間: {result.execution_time:.3f}秒")
        
        # システム情報取得
        print("\n[2] システム情報取得:")
        result = await controller.run_command("Get-ComputerInfo | Select-Object CsName, OsName | ConvertTo-Json")
        if result.success:
            print(f"  出力: {result.output}")
        else:
            print(f"  エラー: {result.error}")
        
        # タイムアウト設定付きコマンド
        print("\n[3] タイムアウト付きコマンド:")
        result = await controller.run_command("Start-Sleep -s 1; Write-Output 'Completed after delay'", timeout=2.0)
        print(f"  出力: {result.output}")
        
        # エラー処理
        print("\n[4] エラー処理:")
        result = await controller.run_command("Get-NonExistentCommand")
        if not result.success:
            print(f"  エラー: {result.error}")

async def main():
    await async_example()
    print("\n===== 完了 =====")

if __name__ == "__main__":
    asyncio.run(main()) 