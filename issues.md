# 現状の課題と改善方針

## 優先度の高い課題

1. **テスト網羅性の向上**
   - 課題: テストケースのカバレッジを向上させる必要がある
   - 改善方針: 境界値テストやエラーケーステストを追加する

2. **ドキュメント整備**
   - 課題: 使用方法や内部設計に関するドキュメントが不足している
   - 改善方針: READMEの拡充とAPIドキュメントの整備

3. **MDCルールとコードベースの整合性**
   - 課題: MDCに記載されているルールと実際のコードベースに不整合がある
   - 改善方針: 以下の不整合を解消する
     - `green.mdc`で指定されている`result`型を使用したエラー処理が一部のコードで実装されていない
     - テスト構造が`python_test.mdc`で指定された構造と完全に一致していない

4. **PowerShellコマンド実行の互換性問題**
   - 課題: PowerShell環境でのパス処理やコマンド構文に関する互換性問題が存在する
   - 改善方針: 以下の問題に対処する
     - 長いパス名や複雑なパス名を含むコマンドでのバッファオーバーフロー
     - Unix/Linux系コマンド構文とPowerShellコマンドレットの構文の違いによるエラー
     - 複数ファイルの一括処理をクロスプラットフォームで動作させるためのスクリプト改善

## ユーザー対応の課題

**ユーザー対応課題: PowerShellコンソールバッファサイズエラー**
- 課題: 長いコマンドや大量の出力を処理する際にPSReadLineのバッファサイズ例外が発生する
- 症状: コマンド実行中に以下のエラーが表示され、コマンドが完了しない
  ```
  System.ArgumentOutOfRangeException: The value must be greater than or equal to zero and less than the console's buffer size in that dimension. (Parameter 'top')
  ```
- 発生条件:
  - 複数の長いパスを含むコマンド（例：`ruff check . --fix && black . && autoflake ...`）を実行
  - 多くの警告やエラーを出力する静的解析ツールを実行
- 対応策:
  - PowerShellプロファイルに以下の設定を追加
    ```powershell
    # PowerShellプロファイル（$PROFILE）に追加
    $bufferSize = $Host.UI.RawUI.BufferSize
    $bufferSize.Width = 200
    $bufferSize.Height = 5000
    $Host.UI.RawUI.BufferSize = $bufferSize
    ```
  - 出力が多いコマンドはファイルにリダイレクト
    ```powershell
    ruff check . --fix > ruff_output.txt
    black . > black_output.txt
    autoflake --in-place --remove-unused-variables --remove-all-unused-imports -r . > autoflake_output.txt
    ```
  - 複数コマンドを別々に実行する
- 根本原因: PowerShellのPSReadLineモジュールには、コンソールのバッファサイズを超える出力を処理する際に発生する制限があります。これはPowerShell自体の制限であり、ライブラリ側では対応できません。

## 補足事項

- PowerShell 7の環境依存性への対応
- パフォーマンス最適化（大量のコマンド実行時）
- セキュリティ強化（入力検証の徹底）

## 文字化け問題

### 問題点
- PowerShellコントローラーのターミナル出力で`stream_handler.py`が文字化けする問題が発生
- Cursorエディタで直接開いた場合は文字化けしない

### 調査結果
- システムのデフォルトエンコーディングは`UTF-8`(CodePage: 65001)
- PowerShellの出力エンコーディングは`Shift-JIS`(CodePage: 932)
- Pythonファイルは`UTF-8`でエンコードされている
- `StreamHandler`クラスでは以下の処理を行っている：
  - PowerShell側に`$OutputEncoding = [System.Text.Encoding]::UTF8`を設定する初期化スクリプトを送信
  - Pythonからの出力はsettings.encoding（デフォルト：UTF-8）でエンコード
  - PowerShellからの入力はsettings.encoding（デフォルト：UTF-8）でデコード
- ターミナル上で設定と実際の動作に不一致がある可能性がある

### 原因の可能性
1. PowerShell 7のターミナルの出力エンコーディングが`Shift-JIS`だが、Pythonからは`UTF-8`として処理している
2. 初期化スクリプトが正しく適用されていない、または効果がない
3. PowerShellプロセスの起動時にエンコーディング設定が適切に継承されていない
4. ターミナルの文字コード設定(CodePage: 932)とファイルの文字コード(UTF-8)の不一致

### 対応案
1. すべてのPythonファイルの先頭に`# -*- coding: utf-8 -*-`を明示的に追加
2. `StreamHandler`クラスのエンコーディング処理を改善：
   - システムの実際のエンコーディングを検出して適応させる機能の追加
   - PowerShellの出力エンコーディングが`Shift-JIS`の場合の互換性対応
3. PowerShellプロセス開始時のコマンドラインにエンコーディング指定を追加：
   ```powershell
   pwsh -NoProfile -OutputEncoding UTF8 -InputEncoding UTF8 ...
   ```
4. デバッグログを強化して、実際のエンコード/デコード処理の動作確認機能を追加

### 優先度
中

### 担当者
未割り当て 