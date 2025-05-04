# PowerShell Controller for MCP

PowerShell 7をPythonから制御するためのシンプルなパッケージです。MCPのためのセッション管理とコマンド実行に特化しています。

## 機能

- PowerShellセッションでのコマンド実行
- 複数コマンドの連続実行
- 確実なプロセス管理
- シンプルなエラーハンドリング

## インストール

開発版をインストールする場合：

```bash
pip install -e .
```

## 使用例

```python
from powershell_controller.simple import SimplePowerShellController

# コントローラーの初期化
controller = SimplePowerShellController()

# 単一コマンドの実行
result = controller.execute_command("Write-Output 'Hello, PowerShell!'")
print(result)  # 出力: Hello, PowerShell!

# 複数コマンドの実行
commands = [
    "Write-Output 'Command 1'",
    "Write-Output 'Command 2'",
    "Write-Output 'Command 3'"
]
results = controller.execute_commands_in_session(commands)
for i, result in enumerate(results):
    print(f"Command {i+1} output: {result}")
```

## テスト

テストを実行するには：

```bash
pytest tests/
```

## 開発環境のセットアップ

1. リポジトリのクローン：
```bash
git clone https://github.com/yourusername/powershell_controller.git
cd powershell_controller
```

2. 依存関係のインストール：
```bash
pip install -e .
```

## 要件

- Python 3.11以上
- PowerShell 7（Path: C:\Program Files\PowerShell\7\pwsh.exe）
- Windows OS
- psutil

## 注意事項

このパッケージは、MCPのためのPowerShell制御に特化して設計されています。
シンプルで堅牢な実装を重視し、必要最小限の機能のみを提供します。

## ライセンス

MIT License 