#!/usr/bin/env python3
"""
PowerShell Controllerの簡単な使用例：
基本的なディレクトリ操作（非同期版）
"""
import asyncio
from powershell_controller.session import PowerShellSession

async def main():
    # withブロックでセッションを管理
    async with PowerShellSession() as session:
        # 現在のディレクトリの内容を取得
        result = await session.execute("Get-ChildItem")
        print("現在のディレクトリ:")
        print(result)
        
        # 親ディレクトリに移動
        await session.execute("Set-Location ..")
        
        # 移動後のディレクトリ内容を取得
        result = await session.execute("Get-ChildItem")
        print("\n親ディレクトリ:")
        print(result)

if __name__ == "__main__":
    asyncio.run(main()) 