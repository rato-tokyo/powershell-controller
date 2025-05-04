# PowerShell Controller

PowerShell 7をPythonから制御するためのパッケージです。セッションを維持したままPowerShellコマンドを実行することができます。

## 機能

- PowerShellセッションの維持
- コマンドの実行と結果の取得
- セッション状態の保持（変数、カレントディレクトリなど）
- エラーハンドリング
- バックグラウンドジョブのサポート

## インストール

開発版をインストールする場合：

```bash
pip install -e .[dev]
```

## 使用例

```python
from powershell_controller import PowerShellController

# コントローラーの初期化
controller = PowerShellController()

try:
    # コマンドの実行
    result = controller.execute_command("Write-Output 'Hello, PowerShell!'")
    print(result)  # 出力: Hello, PowerShell!

    # ディレクトリの移動
    controller.execute_command("cd ..")
    
    # 変数の設定と使用
    controller.execute_command("$test_var = 'test_value'")
    result = controller.execute_command("Write-Output $test_var")
    print(result)  # 出力: test_value

finally:
    # セッションの終了
    controller.close()
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

2. 開発用依存関係のインストール：
```bash
pip install -e .[dev]
```

## 要件

- Python 3.6以上
- PowerShell 7（Path: C:\Program Files\PowerShell\7\pwsh.exe）
- Windows OS

## ライセンス

MIT License 