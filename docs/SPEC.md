# PowerShellコントローラー仕様書

## 概要

PowerShellコントローラーは、PythonからPowerShellを操作するためのライブラリです。シンプルなインターフェースを提供し、同期処理と非同期処理の両方をサポートします。

## 機能一覧

### 基本機能

- PowerShellコマンドの実行（同期/非同期）
- PowerShellスクリプトの実行（同期/非同期）
- コマンド実行結果の取得と解析
- エラーハンドリング（例外ベース/Result型）
- PowerShellセッションの管理

### 拡張機能

- JSON形式での結果取得
- 環境変数操作
- タイムアウト制御
- 特殊文字のエスケープ処理
- エンコーディング対応（Windows日本語環境）
- インターフェース指向設計（抽象基底クラス）

## 使用例

### 基本的な使用方法（同期API）

```python
from py_pshell import PowerShellController

# コントローラーの初期化
controller = PowerShellController()

try:
    # コマンドの実行
    output = controller.execute_command("Get-Process | Select-Object -First 5")
    print(output)
    
    # スクリプトの実行
    script = """
    $data = @{Name="test"; Value=123}
    $data | ConvertTo-Json
    """
    result = controller.execute_script(script)
    print(result)
finally:
    # 必ずリソースを解放
    controller.close_sync()
```

### 非同期APIの使用例

```python
import asyncio
from py_pshell import PowerShellController

async def main():
    # コンテキストマネージャーとして使用
    async with PowerShellController() as controller:
        # 非同期コマンド実行
        result = await controller.run_command("Get-Process | Select-Object -First 5")
        if result.success:
            print(result.output)
        else:
            print(f"エラー: {result.error}")
        
        # 非同期スクリプト実行
        script_result = await controller.run_script("Get-Date | ConvertTo-Json")
        print(script_result.output)

# イベントループの実行
asyncio.run(main())
```

### Result型を使用したエラーハンドリング

```python
from py_pshell import PowerShellController

controller = PowerShellController()

try:
    # Result型を使用したエラーハンドリング
    result = controller.execute_command_result("Get-Process -Name NonExistentProcess")
    
    if result.is_ok():
        print(f"成功: {result.unwrap()}")
    else:
        error = result.unwrap_err()
        print(f"エラー: {error}")
        # エラー情報の詳細を取得可能
        print(f"エラー種別: {type(error).__name__}")
finally:
    controller.close_sync()
```

### インターフェースの使用例

```python
from py_pshell import PowerShellControllerProtocol, CommandResultProtocol
from typing import Dict, Any, Optional

class MockCommandResult(CommandResultProtocol):
    # CommandResultProtocolの実装
    @property
    def output(self) -> str:
        return "モック出力"
        
    # その他のプロパティとメソッドも実装...

class CustomPowerShellController(PowerShellControllerProtocol):
    # カスタムコントローラーの実装
    async def run_command(self, command: str, timeout: Optional[float] = None) -> CommandResultProtocol:
        # カスタム実装
        pass
        
    # その他のメソッドも実装...
```

## 対象外の機能

以下の機能は現在サポートしていません：

- PowerShellリモーティング（PSRemoting）
- インタラクティブなプロンプト応答
- PowerShellモジュールのインストール管理
- 複雑なオブジェクト（COM、.NETオブジェクトなど）の直接操作
- クレデンシャル認証による実行

## 実装の制約事項

- Windows環境ではPowerShell 5.1以上、またはPowerShell Core 7.0以上が必要
- Linux/macOS環境ではPowerShell Core 7.0以上が必要
- 非同期操作にはasyncioが使用されており、Python 3.6以上が必要
- 複数コマンドの同時実行は可能ですが、シングルセッションでは順次実行されます
- 大量のデータ出力を伴うコマンドは、メモリ使用量に注意が必要です 