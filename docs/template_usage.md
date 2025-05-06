# PowerShellコントローラーのテンプレート使用ガイド

## 概要

このドキュメントでは、PowerShellコントローラーのテンプレートの使用方法と、再利用可能なインフラ層の活用方法について説明します。

## ディレクトリ構造

```
infra/
  utils/
    process_manager.py  - 非同期プロセス管理
    test_helper.py      - テスト用ヘルパー
    ipc.py             - プロセス間通信
    errors.py          - エラー定義
templates/
  session_template.py    - セッション管理テンプレート
```

## テンプレートの使用方法

1. セッション管理クラスの作成
   ```python
   from templates.session_template import BaseSessionTemplate
   
   class MyPowerShellSession(BaseSessionTemplate):
       async def initialize(self) -> None:
           # セッションの初期化処理を実装
           pass
           
       async def cleanup(self) -> None:
           # クリーンアップ処理を実装
           pass
           
       async def execute(self, command: str) -> Any:
           # コマンド実行処理を実装
           pass
   ```

2. インフラ層の活用
   ```python
   from infra.utils.process_manager import AsyncProcessManager
   from infra.utils.test_helper import AsyncTestHelper
   from infra.utils.ipc import IPCProtocol
   
   # プロセス管理の使用例
   process_manager = AsyncProcessManager()
   result = await process_manager.run_in_executor(some_function)
   
   # テストヘルパーの使用例
   await AsyncTestHelper.wait_for_condition(
       lambda: check_condition(),
       timeout=5.0
   )
   
   # IPCプロトコルの使用例
   protocol = IPCProtocol()
   message = protocol.create_command_message("some command")
   ```

## エラー処理

エラー処理は標準化されており、以下のエラークラスが提供されています：

- `PowerShellError`: 基底エラークラス
- `ProcessError`: プロセス関連のエラー
- `TimeoutError`: タイムアウトエラー
- `CommunicationError`: 通信エラー

エラー処理の例：
```python
try:
    result = await session.execute("some command")
except ProcessError as e:
    logger.error(f"プロセスエラー: {e}")
except TimeoutError as e:
    logger.error(f"タイムアウト: {e}")
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
   - `AsyncProcessManager`の活用
   - 適切なタイムアウト設定
   - エラー回復メカニズムの実装

4. テスト
   - `AsyncTestHelper`の活用
   - モックの適切な使用
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