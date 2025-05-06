# py-pshell-core

PowerShell 7コントローラーのコア機能を提供するパッケージです。

## 機能

- PowerShellプロセスの管理
- コマンドの実行とレスポンス処理
- セッション管理
- エラーハンドリング

## 使用方法

```python
from py_pshell_core import SimplePowerShellController

# コントローラーのインスタンス化
controller = SimplePowerShellController()

# コマンド実行
result = controller.execute("Get-Process")
if result.success:
    print(result.output)
else:
    print(f"エラー: {result.error}")
``` 