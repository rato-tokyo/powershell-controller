# py-pshell-async

PowerShell 7コントローラーの非同期処理機能を提供するパッケージです。

## 機能

- 非同期イベントループの管理
- タスク管理とトラッキング
- 並行処理の制御と最適化
- 非同期ユーティリティ関数

## 使用方法

```python
from py_pshell_async import AsyncLoopManager, TaskManager, gather_with_concurrency

# イベントループ管理
loop_manager = AsyncLoopManager()

# 非同期関数を同期的に実行
result = loop_manager.run_in_loop(async_function, arg1, arg2)

# 並列実行（同時実行数を制限）
async def main():
    tasks = [fetch_data(i) for i in range(100)]
    results = await gather_with_concurrency(10, *tasks)  # 最大10同時実行
    
    # TaskManagerでタスクを追跡
    task_manager = TaskManager()
    task = task_manager.create_task(some_long_running_coroutine())
    
    # 完了を待機
    await task_manager.wait_for_all()
``` 