# py-pshell-utils

PowerShell 7コントローラーのユーティリティ機能を提供するパッケージです。

## 機能

- 設定管理
- 結果処理ヘルパー
- エラー型定義
- 共通ユーティリティ関数

## 使用方法

```python
from py_pshell_utils.config import PowerShellControllerSettings
from py_pshell_utils.result_helper import ResultHandler

# 設定の読み込み
settings = PowerShellControllerSettings()

# 結果ハンドラーの使用
result = some_function()
handler = ResultHandler(result)
if handler.is_success():
    data = handler.unwrap()
else:
    error = handler.unwrap_err()
``` 