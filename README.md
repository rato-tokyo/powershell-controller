# PyPShell (py-pshell)

PowerShell 7のセッション管理とコマンド実行を行うPythonライブラリです。非同期処理と高機能なエラーハンドリングを備えています。

## 特徴

- PowerShell 7のコマンド実行と制御（同期・非同期両対応）
- セッション管理とディレクトリナビゲーション
- 堅牢なエラーハンドリングとリトライ機能
- Result型を利用した安全なエラーハンドリング
- 実行時型チェック (beartype) によるバグ検出
- 構造化されたログ出力（loguru対応）
- JSON形式のデータ処理
- 型安全性（mypy対応）

## 最近の変更点

- **パッケージ名変更**: `powershell_controller`から`py-pshell`に変更
- **コードベースの統合**: `controller.py`の機能を`simple.py`に統合し、インターフェースを簡素化
- **警告処理の改善**: 非同期処理での警告を削減し、より安定した実行を実現
- **テスト機能の強化**: モックを活用した単体テストの拡充

## プロジェクト構造

```
src/py_pshell/
├── __init__.py              # パッケージエクスポート
├── simple.py                # メイン機能（SimplePowerShellController）
├── command_executor.py      # コマンド実行機能
├── session_manager.py       # セッション管理機能
├── error_handler.py         # エラー処理機能
├── core/                    # コア機能
│   ├── errors/              # エラー定義
│   └── session/             # セッション実装
├── infra/                   # インフラ層
│   ├── async_utils/         # 非同期ユーティリティ
│   ├── ipc/                 # プロセス間通信
│   └── process.py           # プロセス管理
└── utils/                   # ユーティリティ
    ├── config.py            # 設定管理
    └── result_helper.py     # Result型ヘルパー
```

## 要件

- Python 3.8以上
- PowerShell 7.x
- Windows環境（Linux/macOSも基本的に動作）

## インストール

```bash
# 基本インストール
pip install .

# 開発用パッケージを含むインストール
pip install -e ".[dev]"
```

## 基本的な使用例

```python
from py_pshell import SimplePowerShellController

# コントローラーの初期化
controller = SimplePowerShellController()

# 単一コマンドの実行（同期）
result = controller.execute_command("Write-Output 'Hello, World!'")
print(result)  # "Hello, World!"

# 複数コマンドの実行（セッション維持）
commands = [
    "$var = 'Hello'",
    "Write-Output $var"
]
results = controller.execute_commands_in_session(commands)
print(results)  # ["Hello"]
```

## 同期APIと非同期APIの使い分け

このライブラリは同期APIと非同期API（async/await）の両方を提供しています：

### 同期API（簡単な使用）

```python
from py_pshell import SimplePowerShellController

controller = SimplePowerShellController()

# 同期メソッド
result = controller.execute_command("Get-Process")
print(result)

# リソース解放
controller.close_sync()
```

### 非同期API（高度な使用）

```python
import asyncio
from py_pshell import SimplePowerShellController

async def main():
    # 非同期コンテキストマネージャとして使用
    async with SimplePowerShellController() as controller:
        # 非同期メソッド
        result = await controller.run_command("Get-Process")
        print(result.output)
        
        # 複数コマンドの実行
        results = await controller.run_commands([
            "Set-Location C:\\temp",
            "Get-ChildItem"
        ])
        
        for result in results:
            print(result.output)

# 非同期実行
asyncio.run(main())
```

## Result型を利用したエラーハンドリング

```python
from py_pshell import SimplePowerShellController

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
from py_pshell.utils.result_helper import ResultHandler

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
    # エラーごとの処理
    return f"カスタムエラーメッセージ: {err}"

# ResultHandlerを使ったエラー処理
output = ResultHandler.unwrap_or_else(result, handle_error)
```

## 例外処理とエラーハンドリング

ライブラリは3つのレベルのエラーハンドリングを提供します：

### 1. 例外による方法

```python
from py_pshell import SimplePowerShellController
from py_pshell.core.errors import (
    PowerShellExecutionError,
    PowerShellTimeoutError,
    CommunicationError,
    ProcessError
)

controller = SimplePowerShellController()

try:
    result = controller.execute_command("Get-NonExistentCmdlet")
except PowerShellExecutionError as e:
    print(f"コマンド実行エラー: {e}")
except PowerShellTimeoutError:
    print("タイムアウトが発生しました")
except CommunicationError:
    print("通信エラーが発生しました")
except ProcessError:
    print("プロセスエラーが発生しました")
except Exception as e:
    print(f"その他のエラー: {e}")
```

### 2. Result型による方法

```python
from py_pshell import SimplePowerShellController

controller = SimplePowerShellController()
result = controller.execute_command_result("Get-Process")

# パターン1: 条件分岐による処理
if result.is_ok():
    data = result.unwrap()
    print(f"成功: {data}")
else:
    error = result.unwrap_err()
    print(f"エラー: {error}")

# パターン2: デフォルト値を使用
data = result.unwrap_or("デフォルト値")

# パターン3: エラー時にカスタム関数を実行
def handle_error(err):
    # エラーログを記録
    logger.error(f"エラーが発生: {err}")
    return "エラー発生時のデフォルト値"

from py_pshell.utils.result_helper import ResultHandler
data = ResultHandler.unwrap_or_else(result, handle_error)
```

### 3. コマンド結果オブジェクトによる方法

```python
from py_pshell import SimplePowerShellController

controller = SimplePowerShellController()

# 非同期実行の場合
async def process_command():
    result = await controller.run_command("Get-Process")
    if result.success:
        print(f"出力: {result.output}")
    else:
        print(f"エラー: {result.error}")
        print(f"詳細: {result.details}")
```

## ロギング設定

ライブラリは[loguru](https://github.com/Delgan/loguru)を使用して詳細なログを提供します：

```python
from py_pshell import SimplePowerShellController
from loguru import logger

# ログレベルの設定
logger.remove()  # デフォルトハンドラを削除
logger.add(sys.stderr, level="INFO")  # 標準エラー出力にINFOレベルで出力
logger.add("powershell.log", rotation="10 MB", level="DEBUG")  # ファイルにDEBUGレベルで出力

# 構造化ロギングの活用
logger = logger.bind(component="app", service="powershell")

# コントローラーの初期化
controller = SimplePowerShellController()
```

### ロギングオプションの設定

```python
from py_pshell.utils.config import PowerShellControllerSettings

settings = PowerShellControllerSettings(
    log_level="DEBUG",  # ログレベル設定
    debug_logging=True,  # デバッグログの有効化
)

controller = SimplePowerShellController(settings=settings)
```

## 開発とテスト

```bash
# 依存パッケージのインストール
pip install -e ".[dev]"

# コードスタイルチェック
ruff check .

# 型チェック
mypy src/

# テストの実行（カバレッジレポート付き）
pytest tests/ -v --cov=py_pshell --cov-report=term-missing
```

## 設定のカスタマイズ

```python
from py_pshell.utils.config import (
    PowerShellControllerSettings,
    PowerShellConfig,
    TimeoutConfig
)

config = PowerShellControllerSettings(
    # ロギング設定
    log_level="DEBUG",
    debug_logging=True,
    
    # タイムアウト設定
    timeouts=TimeoutConfig(
        default=60.0,
        startup=30.0,
        execution=15.0,
        read=5.0,
        shutdown=10.0,
        cleanup=10.0
    ),
    
    # PowerShell設定
    powershell=PowerShellConfig(
        path="C:\\Program Files\\PowerShell\\7\\pwsh.exe",
        args=["-NoProfile", "-ExecutionPolicy", "Bypass"],
        encoding="utf-8"
    ),
    
    # リトライ設定
    retry_attempts=3,
    retry_delay=1.0
)

controller = SimplePowerShellController(settings=config)
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
from py_pshell.utils.config import PowerShellControllerSettings

settings = PowerShellControllerSettings(
    retry_attempts=5,  # 最大試行回数
    retry_delay=1.0,   # 初期待機時間（秒）
)

controller = SimplePowerShellController(settings=settings)
```

## 環境変数による設定

```bash
# PowerShell Controller設定
export PS_CTRL_LOG_LEVEL=INFO
export PS_CTRL_DEBUG_LOGGING=true
export PS_CTRL_PS_PATH="C:\Program Files\PowerShell\7\pwsh.exe"
export PS_CTRL_RETRY_ATTEMPTS=3
export PS_CTRL_RETRY_DELAY=1.0
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

5. 非同期コードでの警告
   - `asyncio.create_task`使用時の警告が出る場合は、適切にタスクを管理してください
   - `await`し忘れたコルーチンがないか確認してください

## ライセンス

MIT License 