# PowerShell Controller for Python

Pythonから簡単にPowerShellを操作するためのライブラリです。
同期・非同期APIを提供し、Windows/Linux/macOSで動作します。

## 特徴

- シンプルで直感的なAPI
- 同期・非同期の両方のインターフェース
- 強力なエラーハンドリング
- タイムアウト処理
- コマンドとスクリプトの両方をサポート
- クロスプラットフォーム対応（Windows, Linux, macOS）
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

## カスタマイズ

設定をカスタマイズする例:

```python
from py_pshell import PowerShellController, PowerShellControllerSettings

# コントローラー設定
settings = PowerShellControllerSettings(
    powershell_executable="pwsh",  # PowerShellの実行パス
    timeout=PowerShellControllerSettings.TimeoutSettings(
        startup=15.0,  # 起動時のタイムアウト
        shutdown=3.0,  # シャットダウン時のタイムアウト
        default=10.0,  # デフォルトのタイムアウト
    ),
    encoding="utf-8",  # 文字エンコーディング
    debug=True  # デバッグモード
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
finally:
    controller.close_sync()
```

## ライセンス

MITライセンス 