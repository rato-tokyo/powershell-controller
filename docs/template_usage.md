# PowerShellコントローラーのテンプレート使用ガイド

## 概要

このドキュメントでは、PowerShellコントローラーのテンプレートの使用方法について説明します。このテンプレートを使用することで、独自のPowerShellセッション管理クラスを簡単に作成できます。

## パッケージ構造

```
py_pshell/
├── __init__.py            # パッケージエクスポート定義
├── controller.py          # PowerShellController実装
├── session.py             # PowerShellSession実装
├── config.py              # 設定クラス
├── errors.py              # 例外定義
├── interfaces.py          # インターフェース定義
└── utils/                 # ユーティリティ関数
    ├── __init__.py
    └── ... その他ユーティリティ

templates/
└── session_template.py    # セッション管理テンプレート
```

## テンプレートの使用方法

1. セッション管理クラスの作成
   ```python
   from templates.session_template import BaseSessionTemplate
   from py_pshell.errors import ProcessError, CommunicationError
   
   class MyPowerShellSession(BaseSessionTemplate):
       async def initialize(self) -> None:
           # セッションの初期化処理を実装
           self.process = await asyncio.create_subprocess_exec(
               self.powershell_executable,
               stdin=asyncio.subprocess.PIPE,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE
           )
           
       async def cleanup(self) -> None:
           # クリーンアップ処理を実装
           if self.process and self.process.returncode is None:
               self.process.terminate()
               await self.process.wait()
           
       async def execute(self, command: str) -> str:
           # コマンド実行処理を実装
           if not self.process:
               raise ProcessError("プロセスが初期化されていません")
               
           try:
               self.process.stdin.write(f"{command}\n".encode('utf-8'))
               await self.process.stdin.drain()
               
               # タイムアウト付きで出力を読み取り
               output = await asyncio.wait_for(
                   self.process.stdout.read(1024),
                   timeout=self.timeout
               )
               return output.decode('utf-8')
           except asyncio.TimeoutError:
               raise TimeoutError(f"コマンド実行がタイムアウトしました: {command}")
           except Exception as e:
               raise CommunicationError(f"コマンド実行中にエラーが発生: {e}")
   ```

## エラー処理

エラー処理は標準化されており、以下のエラークラスが提供されています：

- `PowerShellError`: 基底エラークラス
- `PowerShellExecutionError`: コマンド実行エラー
- `PowerShellTimeoutError`: タイムアウトエラー
- `PowerShellStartupError`: 起動エラー
- `PowerShellShutdownError`: 終了エラー
- `ProcessError`: プロセス関連のエラー
- `CommunicationError`: 通信エラー

エラー処理の例：
```python
from py_pshell.errors import PowerShellExecutionError, PowerShellTimeoutError

try:
    result = await session.execute("some command")
except PowerShellExecutionError as e:
    logger.error(f"実行エラー: {e}")
except PowerShellTimeoutError as e:
    logger.error(f"タイムアウト: {e}")
except ProcessError as e:
    logger.error(f"プロセスエラー: {e}")
except CommunicationError as e:
    logger.error(f"通信エラー: {e}")
```

## ベストプラクティス

1. テンプレートの継承
   - 必要なメソッドを適切にオーバーライド
   - 基本機能の再利用を最大限活用

2. エラー処理
   - 適切なエラークラスの使用
   - エラー情報の詳細な記録
   - リトライ可能なエラーの処理

3. 非同期処理
   - asyncio関数の適切な使用
   - 適切なタイムアウト設定
   - エラー回復メカニズムの実装

4. テスト
   - インターフェースを実装したモックの活用
   - テスト用のヘルパーメソッドの使用
   - エッジケースのテスト

## 注意事項

1. セッション管理
   - リソースの適切な解放
   - タイムアウトの適切な設定
   - エラー発生時のクリーンアップ

2. プロセス管理
   - 同時実行数の制御
   - メモリリークの防止
   - ゾンビプロセスの防止

3. 通信プロトコル
   - メッセージフォーマットの遵守
   - エラー通知の適切な処理
   - タイムアウトの考慮 