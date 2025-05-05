# PowerShell Controller

PowerShell 7のセッション管理とコマンド実行を行うPythonライブラリです。MCPのための高度な制御機能を提供します。

## 特徴

- PowerShell 7のコマンド実行と制御
- セッション管理とディレクトリナビゲーション
- 堅牢なエラーハンドリングとリトライ機能
- 構造化されたログ出力（rich対応）
- JSON形式のデータ処理
- 型安全性（mypy対応）

## 要件

- Python 3.8以上
- PowerShell 7.x
- Windows環境

## インストール

```bash
# 基本インストール
pip install .

# 開発用パッケージを含むインストール
pip install -e ".[dev]"
```

## 基本的な使用例

```python
from powershell_controller.simple import SimplePowerShellController

# コントローラーの初期化
controller = SimplePowerShellController()

# 単一コマンドの実行
result = controller.execute_command("Write-Output 'Hello, World!'")
print(result)  # "Hello, World!"

# 複数コマンドの実行（セッション維持）
commands = [
    "$var = 'Hello'",
    "Write-Output $var"
]
results = controller.execute_commands_in_session(commands)
print(results)  # ["Hello"]

# JSON形式のデータ処理
json_result = controller.execute_command("@{ 'key' = 'value'; 'data' = @(1, 2, 3) }")
print(json_result)  # {'key': 'value', 'data': [1, 2, 3]}
```

## 高度な使用例

### セッション内でのディレクトリ移動

```python
commands = [
    "Set-Location C:\\temp",  # ディレクトリ移動
    "New-Item -ItemType Directory -Name 'test'",  # ディレクトリ作成
    "Set-Location .\\test",  # 作成したディレクトリに移動
    "$PWD.Path"  # 現在のパスを取得
]
results = controller.execute_commands_in_session(commands)
```

### スクリプトの実行

```python
script = """
$data = @{
    'name' = 'test'
    'values' = @(1, 2, 3)
}
$data | ConvertTo-Json
"""
result = controller.execute_script(script)
```

## 開発とテスト

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# コードスタイルチェック
ruff check .

# 型チェック
mypy src/

# テストの実行（カバレッジレポート付き）
pytest tests/ -v --cov=powershell_controller --cov-report=term-missing
```

## エラーハンドリング

```python
from powershell_controller.simple import (
    PowerShellExecutionError,
    PowerShellTimeoutError
)

try:
    result = controller.execute_command("Some-Command", timeout=30)
except PowerShellTimeoutError:
    print("コマンドがタイムアウトしました")
except PowerShellExecutionError as e:
    print(f"エラーが発生しました: {e}")
```

## 設定のカスタマイズ

```python
from powershell_controller.simple import (
    PowerShellControllerConfig,
    RetryConfig
)

config = PowerShellControllerConfig(
    log_level="DEBUG",
    log_file="powershell.log",
    retry_config=RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=10.0
    )
)

controller = SimplePowerShellController(config=config)
```

## トラブルシューティング

1. PowerShellのパスが見つからない場合
   - `PowerShellControllerConfig`で正しいパスを指定してください
   - デフォルトパス: `C:\Program Files\PowerShell\7\pwsh.exe`

2. JSON変換エラー
   - PowerShellのハッシュテーブルは自動的にJSON形式に変換されます
   - 複雑なオブジェクトは`ConvertTo-Json -Depth`を使用してください

3. タイムアウトエラー
   - `execute_command`の`timeout`パラメータを調整してください
   - 長時間実行コマンドは適切なタイムアウト値を設定してください

## ライセンス

MIT License 