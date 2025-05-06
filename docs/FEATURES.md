# PowerShellコントローラー機能一覧

このドキュメントでは、PowerShellコントローラーの提供する機能について詳細に説明します。

## コアクラス

### PowerShellController

PowerShellを操作するためのメインインターフェース。同期APIと非同期APIの両方を提供します。

#### 初期化オプション

```python
controller = PowerShellController(settings=PowerShellControllerSettings())
```

- `settings`: PowerShellControllerSettingsオブジェクト。設定のカスタマイズに使用します。

### CommandResult

コマンド実行結果を表すクラス。

```python
result = await controller.run_command("Get-Process")
```

- `output`: コマンドの標準出力（str）
- `error`: コマンドのエラー出力（str）
- `success`: コマンドが成功したかどうか（bool）
- `command`: 実行されたコマンド（str）
- `execution_time`: 実行にかかった時間（秒）（float）

## インターフェース

### PowerShellControllerProtocol

PowerShellControllerの抽象インターフェース。テストやカスタム実装のための基底クラスです。

```python
from py_pshell import PowerShellControllerProtocol

class MyCustomController(PowerShellControllerProtocol):
    # インターフェースの実装
    async def run_command(self, command: str, timeout: Optional[float] = None):
        # 実装...
        pass
    
    # その他のメソッドも実装...
```

### CommandResultProtocol

CommandResultの抽象インターフェース。カスタム結果クラスのための基底クラスです。

```python
from py_pshell import CommandResultProtocol

class MyCustomResult(CommandResultProtocol):
    @property
    def output(self) -> str:
        # 実装...
        return "カスタム出力"
    
    # その他のプロパティとメソッドも実装...
```

## 同期API

### execute_command

PowerShellコマンドを同期的に実行します。

```python
output = controller.execute_command("Get-Process", timeout=10.0)
```

- `command`: 実行するPowerShellコマンド
- `timeout`: コマンド実行のタイムアウト（秒）
- 戻り値: コマンドの出力（str）
- 例外: PowerShellExecutionError, PowerShellTimeoutError

### execute_script

PowerShellスクリプトを同期的に実行します。複数行のスクリプトに対応しています。

```python
output = controller.execute_script("""
$data = Get-Process | Select-Object -First 5
$data | Format-Table
""", timeout=10.0)
```

- `script`: 実行するPowerShellスクリプト
- `timeout`: スクリプト実行のタイムアウト（秒）
- 戻り値: スクリプトの出力（str）
- 例外: PowerShellExecutionError, PowerShellTimeoutError

### execute_command_result

PowerShellコマンドを実行し、Result型で結果を返します。

```python
result = controller.execute_command_result("Get-Process", timeout=10.0)
if result.is_ok():
    output = result.unwrap()
else:
    error = result.unwrap_err()
```

- `command`: 実行するPowerShellコマンド
- `timeout`: コマンド実行のタイムアウト（秒）
- 戻り値: Result[str, PowerShellError]
  - 成功: Ok(output)
  - 失敗: Err(error)

### execute_script_result

PowerShellスクリプトを実行し、Result型で結果を返します。

```python
result = controller.execute_script_result("Get-Process | Select-Object -First 5", timeout=10.0)
```

- `script`: 実行するPowerShellスクリプト
- `timeout`: スクリプト実行のタイムアウト（秒）
- 戻り値: Result[str, PowerShellError]
  - 成功: Ok(output)
  - 失敗: Err(error)

## 非同期API

### run_command

PowerShellコマンドを非同期で実行します。

```python
result = await controller.run_command("Get-Process", timeout=10.0)
```

- `command`: 実行するPowerShellコマンド
- `timeout`: コマンド実行のタイムアウト（秒）
- 戻り値: CommandResult

### run_script

PowerShellスクリプトを非同期で実行します。

```python
result = await controller.run_script("""
$data = Get-Process | Select-Object -First 5
$data | Format-Table
""", timeout=10.0)
```

- `script`: 実行するPowerShellスクリプト
- `timeout`: スクリプト実行のタイムアウト（秒）
- 戻り値: CommandResult

## ユーティリティメソッド

### get_json

PowerShellコマンドを実行し、結果をJSON形式で解析して返します。

```python
data = controller.get_json("Get-Process | Select-Object -First 5 | ConvertTo-Json")
```

- `command`: 実行するPowerShellコマンド（ConvertTo-Jsonを含むこと）
- `timeout`: コマンド実行のタイムアウト（秒）
- 戻り値: 解析されたJSONデータ（Dict[str, Any]）
- 例外: PowerShellExecutionError, PowerShellTimeoutError, ValueError（JSON解析エラー）

### get_environment_variable

PowerShell環境変数の値を取得します。

```python
value = controller.get_environment_variable("PATH")
```

- `name`: 環境変数名
- 戻り値: 環境変数の値（str）
- 例外: PowerShellExecutionError

### set_environment_variable

PowerShell環境変数を設定します。

```python
controller.set_environment_variable("TEST_VAR", "テスト値")
```

- `name`: 環境変数名
- `value`: 設定する値
- 例外: PowerShellExecutionError

## セッション管理

### close

PowerShellセッションを非同期で閉じます。

```python
await controller.close()
```

### close_sync

PowerShellセッションを同期的に閉じます。

```python
controller.close_sync()
```

## コンテキストマネージャーサポート

PowerShellControllerは非同期コンテキストマネージャーとして使用できます。

```python
async with PowerShellController() as controller:
    result = await controller.run_command("Get-Process")
```

## 設定オプション

### PowerShellControllerSettings

```python
settings = PowerShellControllerSettings(
    powershell=PowerShellConfig(
        executable=None,  # PowerShell実行ファイルのパス
        arguments=["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass"],
        encoding="utf-8"  # PowerShellの入出力エンコーディング
    ),
    timeout=TimeoutConfig(
        default=30.0,     # デフォルトのタイムアウト（秒）
        startup=10.0,     # 起動時のタイムアウト（秒）
        shutdown=5.0      # 終了時のタイムアウト（秒）
    ),
    use_mock=False        # モックモードを使用するかどうか（テスト用）
)
``` 