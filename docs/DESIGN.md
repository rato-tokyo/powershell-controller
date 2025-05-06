# PowerShellコントローラー設計ドキュメント

## アーキテクチャ概要

PowerShellコントローラーは、以下のコンポーネントから構成されています：

```
+------------------------+
| PowerShellController   |      ユーザーに公開されるメインインターフェース
+------------------------+
          |
          v
+------------------------+
| PowerShellSession      |      PowerShellプロセスとの通信を管理
+------------------------+
          |
          v
+------------------------+
| PowerShellProcess      |      実際のPowerShellプロセスのライフサイクルを管理
+------------------------+
```

## モジュール構成

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
```

## 主要コンポーネント詳細

### 1. インターフェース層 (interfaces.py)

抽象基底クラスを定義し、テストとモックを容易にします。

- `CommandResultProtocol`: コマンド実行結果のインターフェース
- `PowerShellControllerProtocol`: PowerShellコントローラーのインターフェース

### 2. コントローラー層 (controller.py)

ユーザーインターフェースを提供するメインクラスです。

- `CommandResult`: コマンド実行結果を表すデータクラス
- `PowerShellController`: PowerShellセッションの管理と操作を行うクラス
  - 同期APIと非同期APIの両方を提供
  - Result型を使用したエラーハンドリングをサポート
  - イベントループ管理を内蔵

### 3. セッション層 (session.py)

PowerShellプロセスとの通信を管理します。

- `PowerShellSession`: PowerShellプロセスのライフサイクルとコマンド実行を管理
  - プロセスの起動と終了
  - コマンドの送信と結果の受信
  - エラー処理とタイムアウト管理

### 4. 設定層 (config.py)

アプリケーションの設定を管理します。

- `PowerShellConfig`: PowerShellの設定（実行ファイル、引数、エンコーディングなど）
- `TimeoutConfig`: タイムアウト設定（起動、実行、終了）
- `PowerShellControllerSettings`: コントローラー全体の設定

### 5. エラー処理 (errors.py)

例外クラスと、Result型を使用したエラーハンドリングをサポートします。

- `PowerShellError`: 基底例外クラス
- `PowerShellExecutionError`: コマンド実行エラー
- `PowerShellTimeoutError`: タイムアウトエラー
- `PowerShellStartupError`: 起動エラー
- `PowerShellShutdownError`: 終了エラー
- `as_result`: 例外をResult型に変換するデコレータ

### 6. ユーティリティ (utils/)

共通機能を提供します。

- PowerShell実行ファイルの検出
- 一時ファイル作成
- 文字列エスケープ
- パラメータフォーマット

## 実行フロー

### 同期コマンド実行フロー

1. ユーザーが `controller.execute_command()` を呼び出す
2. コントローラーが内部イベントループを取得または作成
3. 非同期実行関数 `run_command()` を別スレッドで実行
4. コントローラーが結果を待機（タイムアウト監視）
5. 結果または例外を返却

### 非同期コマンド実行フロー

1. ユーザーが `await controller.run_command()` を呼び出す
2. セッションオブジェクトがまだ存在しない場合は作成
3. セッションがコマンドを実行し、標準出力/エラー出力を収集
4. コマンド実行結果を `CommandResult` オブジェクトにラップして返却

## スレッド管理

- メインスレッド: ユーザーコードとコントローラーの同期API
- イベントループスレッド: 非同期操作を処理するasyncioイベントループ
- プロセス通信スレッド: PowerShellプロセスとの入出力通信

## エラーハンドリング戦略

1. **例外ベース**:
   - 通常のPython例外を使用
   - 階層化された例外クラスで詳細なエラー情報を提供
   - いつでもtry-exceptで捕捉可能

2. **Result型**:
   - 関数型プログラミングスタイルのエラーハンドリング
   - 例外ではなく戻り値としてエラーを表現
   - `is_ok()`, `unwrap()`, `unwrap_err()` メソッドでアクセス

## 設計上の考慮事項

1. **セッション再利用**:
   - 複数のコマンドに対して単一のPowerShellセッションを再利用
   - 高速な実行とリソース節約を実現

2. **非同期サポート**:
   - asyncioベースの非同期APIを提供
   - イベントループの自動管理によりユーザーの利便性を向上

3. **マルチプラットフォーム対応**:
   - Windows（PowerShell 5.1以上またはPowerShell Core）
   - Linux/macOS（PowerShell Core）

4. **テスト容易性**:
   - インターフェースを使用した依存性注入
   - モックモードのサポート
   - 各コンポーネントが単体でテスト可能

5. **エラー透過性**:
   - PowerShellの実行エラーを適切に捕捉
   - 元のエラーメッセージを保持
   - 詳細なコンテキスト情報を提供

## 使用パターン

1. **シンプルな同期使用**:
   ```python
   controller = PowerShellController()
   try:
       result = controller.execute_command("Get-Process")
   finally:
       controller.close_sync()
   ```

2. **非同期コンテキストマネージャー**:
   ```python
   async with PowerShellController() as controller:
       result = await controller.run_command("Get-Process")
   ```

3. **Result型を使用したエラーハンドリング**:
   ```python
   result = controller.execute_command_result("Get-Process")
   if result.is_ok():
       # 成功処理
   else:
       # エラー処理
   ```

## 拡張性

このアーキテクチャは、以下の方向に拡張可能です：

1. **リモートPowerShell**: PSRemotingをサポートするコントローラー拡張
2. **クレデンシャルサポート**: 異なる認証情報でのPowerShell実行
3. **バッチ処理**: 複数コマンドのバッチ実行と結果の集約
4. **オブジェクトモデル**: PowerShellオブジェクトとPythonオブジェクト間の変換 