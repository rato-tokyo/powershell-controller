# PowerShell Controller

Pythonから簡単にPowerShellを操作するためのライブラリです。Windows, Linux, macOSに対応しています。

## 主な機能

- 簡単なインターフェース: PowerShellコマンドを直感的に実行
- 同期・非同期API: 両方のスタイルをサポート
- エラーハンドリング: 堅牢なエラー処理機能
- Result型: 関数型プログラミングスタイルでのエラーハンドリングをサポート
- カスタマイズ可能: 設定や動作を柔軟に調整可能
- インターフェース指向: テストやモックが容易

## インストール

```bash
pip install py-pshell
```

## 基本的な使い方

### 同期API

```python
from py_pshell import PowerShellController
from py_pshell.errors import PowerShellExecutionError

# コントローラーの初期化
controller = PowerShellController()

try:
    # PowerShellコマンドの実行
    output = controller.execute_command("Get-Process | Select-Object -First 5")
    print(output)
    
    # スクリプトの実行
    script = """
    $data = @{
        Name = "Test"
        Value = 123
    }
    ConvertTo-Json $data
    """
    output = controller.execute_script(script)
    print(output)
    
    # エラーハンドリング
    try:
        output = controller.execute_command("Get-NonExistentCommand")
    except PowerShellExecutionError as e:
        print(f"エラーが発生: {e}")
finally:
    # リソースのクリーンアップ
    controller.close_sync()
```

### 非同期API

```python
import asyncio
from py_pshell import PowerShellController

async def main():
    # コンテキストマネージャーを使用（自動クリーンアップ）
    async with PowerShellController() as controller:
        # コマンド実行と結果取得
        result = await controller.run_command("Get-Process | Select-Object -First 5")
        
        if result.success:
            print(f"出力: {result.output}")
        else:
            print(f"エラー: {result.error}")
        
        # スクリプト実行
        script_result = await controller.run_script("""
        $services = Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object -First 3
        $services | ConvertTo-Json
        """)
        
        print(f"実行時間: {script_result.execution_time:.2f}秒")
        print(script_result.output)
        
        # タイムアウト設定を指定してコマンド実行
        result = await controller.run_command("Start-Sleep -s 2; Write-Output 'Done'", timeout=5.0)
        print(result.output)

# 非同期メイン関数の実行
asyncio.run(main())
```

### Result型を使用したエラーハンドリング

```python
from py_pshell import PowerShellController

controller = PowerShellController()

# Result型を返す関数を使用
result = controller.execute_command_result("Get-Process | Select-Object -First 5")

if result.is_ok():
    # 成功時の処理
    output = result.unwrap()
    print(f"成功: {output}")
else:
    # エラー時の処理
    error = result.unwrap_err()
    print(f"エラー: {error}")

controller.close_sync()
```

## カスタマイズ

設定をカスタマイズする例:

```python
from py_pshell import PowerShellController, PowerShellControllerSettings, TimeoutConfig, PowerShellConfig

# タイムアウト設定
timeout_config = TimeoutConfig(
    default=10.0,  # デフォルトのタイムアウト
    startup=15.0,  # 起動時のタイムアウト
    execution=5.0,  # コマンド実行のタイムアウト
    shutdown=3.0   # シャットダウン時のタイムアウト
)

# PowerShell設定
ps_config = PowerShellConfig(
    path="pwsh",  # PowerShellの実行パス
    arguments=["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass"],
    encoding="utf-8"  # 文字エンコーディング
)

# コントローラー設定
settings = PowerShellControllerSettings(
    powershell=ps_config,
    timeout=timeout_config,
    log_level="INFO"  # ログレベル
)

# カスタム設定でコントローラーを初期化
controller = PowerShellController(settings=settings)
```

## インターフェース指向設計

このライブラリは、抽象基底クラス（ABC）を使用したインターフェース指向設計を採用しています。
テスト用のモック作成や独自の実装に活用できます。

```python
from py_pshell import PowerShellControllerProtocol, CommandResultProtocol
from unittest.mock import AsyncMock, MagicMock

# モックコントローラーの作成
class MockPowerShellController(PowerShellControllerProtocol):
    async def run_command(self, command, timeout=None):
        # モック実装
        pass
    
    # その他のメソッドも実装...

# テストでの使用
def test_with_mock(mock_controller: PowerShellControllerProtocol):
    result = mock_controller.execute_command("Get-Process")
    assert result == "モック出力"
```

## テスト用のモックモード

テストやデモ用にモックモードを利用できます:

```python
from py_pshell import PowerShellController, PowerShellControllerSettings

# モックモードを有効化
settings = PowerShellControllerSettings(use_mock=True)
controller = PowerShellController(settings=settings)

# 実際のPowerShellは呼び出されず、モック応答が返される
output = controller.execute_command("Get-Process")
print(output)  # "モック出力: Get-Process" が表示される
```

## 便利なショートカットメソッド

PowerShellでよく使われる操作のためのショートカットメソッドも用意されています：

```python
from py_pshell import PowerShellController

controller = PowerShellController()

try:
    # JSON取得
    data = controller.get_json("Get-Process | Select-Object -First 3 -Property Name,Id,CPU | ConvertTo-Json")
    for process in data:
        print(f"プロセス: {process['Name']}, ID: {process['Id']}")
    
    # 環境変数の操作
    controller.set_environment_variable("PS_TEST_VAR", "テスト値")
    value = controller.get_environment_variable("PS_TEST_VAR")
    print(f"環境変数: {value}")
    
finally:
    controller.close_sync()
```

## ライセンス

MITライセンス 