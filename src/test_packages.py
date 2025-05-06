#!/usr/bin/env python
"""
パッケージ分割テスト

新しく分割されたパッケージが正しく動作するかテストします。
"""
import sys
import os
import asyncio

# システムパスにsrcを追加
sys.path.append(os.path.join(os.path.dirname(__file__)))

def test_utils_package():
    """
    py_pshell_utilsパッケージが正しく動作するかテストします。
    """
    try:
        from py_pshell_utils import (
            PowerShellControllerSettings,
            ResultHandler, 
            PowerShellError, 
            as_result
        )
        
        # 設定のテスト
        settings = PowerShellControllerSettings()
        print(f"設定テスト: PS_PATH = {settings.get_ps_path()}")
        
        # エラー作成テスト
        error = PowerShellError("テストエラー")
        print(f"エラーテスト: {error}")
        
        # Result関数テスト
        @as_result
        def test_func():
            return "テスト成功"
            
        result = test_func()
        if result.is_ok():
            print(f"Resultテスト: OK - {result.unwrap()}")
        else:
            print(f"Resultテスト: エラー - {result.unwrap_err()}")
            
        print("py_pshell_utils テスト成功")
        return True
        
    except Exception as e:
        print(f"py_pshell_utils テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_async_package():
    """
    py_pshell_asyncパッケージが正しく動作するかテストします。
    """
    try:
        from py_pshell_async import (
            AsyncLoopManager,
            TaskManager,
            run_in_loop,
            gather_with_concurrency
        )
        
        # AsyncLoopManagerのテスト
        loop_manager = AsyncLoopManager()
        
        # 非同期関数の定義
        async def hello_async(name):
            return f"こんにちは、{name}さん！"
        
        # 非同期関数の実行テスト
        result = loop_manager.run_in_loop(hello_async, "テスト")
        print(f"非同期実行テスト: {result}")
        
        # TaskManagerのテスト
        async def test_task_manager():
            task_manager = TaskManager()
            # 簡単なタスク作成
            task = task_manager.create_task(hello_async("タスクマネージャー"))
            result = await task
            return result
            
        task_result = loop_manager.run_in_loop(test_task_manager)
        print(f"タスクマネージャーテスト: {task_result}")
        
        # グローバル関数のテスト
        async def test_gather():
            tasks = [hello_async(f"ユーザー{i}") for i in range(3)]
            return await gather_with_concurrency(2, *tasks)
            
        gather_result = run_in_loop(test_gather)
        print(f"gather_with_concurrencyテスト: {gather_result}")
        
        # クリーンアップ
        loop_manager.close()
        
        print("py_pshell_async テスト成功")
        return True
        
    except Exception as e:
        print(f"py_pshell_async テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_core_package():
    """
    py_pshell_coreパッケージが正しく動作するかテストします。
    """
    try:
        from py_pshell_core import SimplePowerShellController, CommandResult
        
        # コントローラのインスタンス化
        controller = SimplePowerShellController()
        
        # 簡単なコマンド実行（モック）
        result = controller.execute_command("Get-Process")
        print(f"コマンド実行テスト: {result}")
        
        # CommandResult
        cmd_result = CommandResult(output="テスト出力", success=True)
        print(f"CommandResultテスト: {cmd_result}")
        
        print("py_pshell_core テスト成功")
        return True
        
    except Exception as e:
        print(f"py_pshell_core テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """
    メイン関数
    """
    print("パッケージ分割テスト開始")
    
    utils_success = test_utils_package()
    print("\n" + "-" * 50 + "\n")
    
    async_success = test_async_package()
    print("\n" + "-" * 50 + "\n")
    
    core_success = test_core_package()
    print("\n" + "-" * 50 + "\n")
    
    if utils_success and async_success and core_success:
        print("すべてのテストが成功しました！")
        return 0
    else:
        print("一部のテストが失敗しました。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 