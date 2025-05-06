# PowerShell Controller

PowerShell 7のセッション管理とコマンド実行を行うPythonライブラリです。MCPのための高度な制御機能を提供します。

## 特徴

- PowerShell 7のコマンド実行と制御
- セッション管理とディレクトリナビゲーション
- 堅牢なエラーハンドリングとリトライ機能
- Result型を利用した安全なエラーハンドリング
- 実行時型チェック (beartype) によるバグ検出
- 構造化されたログ出力（loguru対応）
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

## Result型を利用したエラーハンドリング

```python
from powershell_controller.simple import SimplePowerShellController

controller = SimplePowerShellController()

# Result型を返すメソッドを使用
result = controller.execute_command_result("Get-Process")

# 成功の場合
if result.is_ok():
    processes = result.unwrap()
    print(f"プロセス数: {len(processes)}")
else:
    # エラーの場合
    error = result.unwrap_err()
    print(f"エラーが発生しました: {error}")

# デフォルト値を指定する場合
processes = result.unwrap_or([])
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

### Result型によるスクリプト実行

```python
from powershell_controller.utils.result_helper import ResultHandler

script = """
try {
    Get-ChildItem -Path 'C:\\NonExistingFolder' -ErrorAction Stop
} catch {
    throw "フォルダが見つかりません"
}
"""

# Result型で結果を取得
result = controller.execute_script_result(script)

# 成功・失敗の確認
if result.is_ok():
    output = result.unwrap()
    print(f"成功: {output}")
else:
    error = result.unwrap_err()
    print(f"エラー: {error}")
    
# ResultHandlerを使った処理
def handle_error(err):
    return f"カスタムエラーメッセージ: {err}"
    
output = ResultHandler.unwrap_or_else(result, handle_error)
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
from powershell_controller.simple import SimplePowerShellController
from powershell_controller.core.errors import (
    PowerShellExecutionError,
    PowerShellTimeoutError
)

controller = SimplePowerShellController()

try:
    result = controller.execute_command("Some-Command", timeout=30)
except PowerShellTimeoutError:
    print("コマンドがタイムアウトしました")
except PowerShellExecutionError as e:
    print(f"エラーが発生しました: {e}")
```

## 設定のカスタマイズ

```python
from powershell_controller.utils.config import (
    PowerShellControllerSettings,
    RetryConfig
)

config = PowerShellControllerSettings(
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

## 堅牢性を向上させる機能

### 実行時型チェック (beartype)

パッケージ全体で実行時型チェックが有効になっており、型の不一致によるバグを検出します。

```python
# beartype設定
from beartype import BeartypeConf
from beartype.claw import beartype_this_package

# 独自の設定を使用する場合
beartype_conf = BeartypeConf(
    is_debug=True,  # 詳細なエラーメッセージを表示
    violation_type=Exception,  # 型違反時に例外を発生
)
beartype_this_package(conf=beartype_conf)
```

### リトライ機能

自動リトライ機能により、一時的なネットワークエラーやプロセス問題を克服します。

```python
from powershell_controller.utils.config import RetryConfig

retry_config = RetryConfig(
    max_attempts=5,  # 最大試行回数
    base_delay=1.0,  # 初期待機時間（秒）
    max_delay=30.0,  # 最大待機時間（秒）
    jitter=0.1      # ランダム変動係数
)

controller = SimplePowerShellController(retry_config=retry_config)
```

## トラブルシューティング

1. PowerShellのパスが見つからない場合
   - `PowerShellControllerSettings`で正しいパスを指定してください
   - デフォルトパス: `C:\Program Files\PowerShell\7\pwsh.exe`

2. JSON変換エラー
   - PowerShellのハッシュテーブルは自動的にJSON形式に変換されます
   - 複雑なオブジェクトは`ConvertTo-Json -Depth`を使用してください

3. タイムアウトエラー
   - `execute_command`の`timeout`パラメータを調整してください
   - 長時間実行コマンドは適切なタイムアウト値を設定してください

4. 型エラー
   - beartype実行時型チェックによるエラーが出た場合は、正しい型のデータを渡しているか確認してください
   - 型注釈と実際の値の型が一致していない可能性があります

## ライセンス

MIT License 

## 設定方法

### 環境変数による設定

```bash
# PowerShell Controller設定
export PS_CTRL_LOG_LEVEL=INFO
export PS_CTRL_LOG_FILE=powershell.log
export PS_CTRL_PS_PATH="C:\Program Files\PowerShell\7\pwsh.exe"
```

### .envファイルによる設定

```ini
# .env
PS_CTRL_LOG_LEVEL=INFO
PS_CTRL_LOG_FILE=powershell.log
PS_CTRL_PS_PATH=C:\Program Files\PowerShell\7\pwsh.exe
```

### コードによる設定

```python
from powershell_controller.utils.config import PowerShellControllerSettings, RetryConfig

settings = PowerShellControllerSettings(
    log_level="DEBUG",
    log_file="powershell.log",
    ps_path=r"C:\Program Files\PowerShell\7\pwsh.exe",
    retry_config=RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=5.0,
        jitter=0.1
    )
)

controller = SimplePowerShellController(config=settings)
```

### 設定の優先順位

1. コードで直接指定された値
2. 環境変数
3. .envファイル
4. デフォルト値 