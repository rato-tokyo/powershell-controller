# PowerShell Controller

PowerShell 7のセッション管理とコマンド実行を行うPythonライブラリです。

## 特徴

- PowerShell 7のコマンド実行
- セッション管理
- エラーハンドリング
- リトライ機能
- ログ機能

## インストール

```bash
pip install .
```

## 使用例

```python
from powershell_controller.simple import SimplePowerShellController

# コントローラーの初期化
controller = SimplePowerShellController()

# コマンドの実行
result = controller.execute_command("Write-Output 'Hello, World!'")
print(result)  # "Hello, World!"

# 複数コマンドの実行
commands = [
    "$var = 'Hello'",
    "Write-Output $var"
]
results = controller.execute_commands_in_session(commands)
print(results)  # ["Hello"]
```

## 開発

```bash
# 開発用パッケージのインストール
pip install -e ".[dev]"

# テストの実行
pytest tests/
```

## ライセンス

MIT License 