# MDCファイル管理ガイド

## 概要
このディレクトリ（`.cursor/rules`）には、AIが利用するMDC（Markdown Cursor）ファイルが格納されています。
MDCファイルは、AIに特定の開発作業を指示するために使用されるCursorのカスタム命令機能を活用したマークダウンファイルです。
以前は「Manual Development Control」と誤って記載されていましたが、正しくは「Markdown Cursor」です。

## ディレクトリ構造

```
.cursor/rules/
├── flows/                  # フローMDCファイル（チャットで実行可能）
│   ├── main/               # メインフロー（完全なフロー）
│   │   ├── code_quality.mdc         # コード品質向上フロー
│   │   ├── issue_improvement.mdc    # 課題改善フロー
│   │   ├── mdc_check.mdc            # MDC整合性確認フロー
│   │   └── requirements_change.mdc  # 仕様変更フロー
│   ├── phases/             # 個別フェーズ
│   │   ├── contract.mdc             # 契約フェーズ
│   │   ├── document.mdc             # ドキュメントフェーズ
│   │   ├── green.mdc                # 実装フェーズ
│   │   ├── red.mdc                  # テスト作成フェーズ
│   │   └── refactor.mdc             # リファクタリングフェーズ
│   └── main.mdc            # 基本ルール（常に最初に添付）
├── docs/                   # 補助的なドキュメントファイル
│   ├── flow_execution.mdc  # フロー実行方法
│   ├── flow_phase.mdc      # flow-phase方針（レガシー）
│   ├── init.mdc            # 初期化時のルール
│   ├── main.mdc            # 基本ルール（参照用）※flows/main.mdcを優先使用
│   ├── manual_reference.mdc # マニュアル参照方式
│   ├── mdc_metamodel.mdc   # MDC構造のメタモデル
│   ├── rail.mdc            # RAIL方針（レガシー）
│   └── tool_constraints.mdc # ツールの制限と対応策
├── environment.mdc         # 環境設定
├── flow_overview.mdc       # フロー概要
├── mdc_reference_index.mdc # MDC参照インデックス
├── python_test.mdc         # Pythonテストルール
└── tool_settings.mdc       # ツール設定
```

## 実行可能なフローMDC

以下のMDCファイルは、チャットコンテキストとして添付することで、AIに特定のワークフローを実行させることができます：

### メインフロー（完全なフロー）
- **requirements_change.mdc**: 仕様変更フロー
- **issue_improvement.mdc**: 課題改善フロー
- **code_quality.mdc**: コード品質向上フロー
- **mdc_check.mdc**: MDC整合性確認フロー

### 個別フェーズ（部分的なフロー）
- **contract.mdc**: 契約フェーズ
- **red.mdc**: テスト作成フェーズ
- **green.mdc**: 実装フェーズ
- **document.mdc**: ドキュメントフェーズ
- **refactor.mdc**: リファクタリングフェーズ

### 基本設定（常時必要）
- **main.mdc**: 基本ルール（常に最初に添付）

## フローMDCの使用方法

フローMDCをチャットで使用するには：

1. `.cursor/rules/flows/main.mdc`を取得
2. 使用したいフローMDC（例：`.cursor/rules/flows/main/requirements_change.mdc`）を取得
3. 両方を以下の形式でカスタム指示として添付：

```
<custom_instructions>
<required_instructions>
[main.mdcの内容]

[フローMDCの内容]
</required_instructions>
</custom_instructions>
```

詳しい使用方法は `.cursor/rules/docs/flow_execution.mdc` を参照してください。

## MDCファイルの整理とメンテナンス

MDCファイルの整理には以下のルールに従ってください：

1. **パス参照の統一**: すべてのMDC参照を相対パスで統一します
   - `flows/main.mdc` を基準とする相対パスを使用してください
   - 絶対パス（`.cursor/rules/...`）は使用しないでください

2. **重複ファイルの回避**: 同じ内容のファイルが複数の場所に存在しないようにします
   - 特に `docs/main.mdc` と `flows/main.mdc` の同期に注意してください
   - 基本的に `flows/main.mdc` を優先して使用してください

3. **レガシーファイルの扱い**: レガシーとマークされたファイルは参照のみとします
   - `rail.mdc` と `flow_phase.mdc` は新規開発では使用しないでください
   - 既存コードの理解のためにのみ参照してください

4. **MDCの追加・削除**: MDCファイルを追加・削除する場合は必ず以下を更新してください
   - `mdc_reference_index.mdc`: 参照情報の更新
   - `README.md`: ディレクトリ構造の更新
   - `flows/main.mdc`: 参照パスの更新

5. **一時ファイルの禁止**: テキストメモなどの一時ファイルはMDCディレクトリに置かないでください
   - 一時ファイルは `environment.mdc` に定義された場所に保存してください

適切にMDCファイルを整理することで、MDCファーストアプローチの効率が向上します。

## エラー検出スクリプト

MDCファーストアプローチのエラー記録を自動化するスクリプトが用意されています：

1. **未記録エラー自動検出スクリプト**: `scripts/auto_mdc_error_check.ps1`
   - PowerShellコマンド履歴から未記録のエラーを検出
   - issues.mdとの整合性をチェック
   - 使用方法: `./auto_mdc_error_check.ps1`

2. **未記録エラー自動記録スクリプト**: `scripts/auto_mdc_error_record.ps1`
   - 検出した未記録エラーをissues.mdに自動追記
   - 使用方法: `./auto_mdc_error_record.ps1`

## MDCファイル整理ルール

1. **一貫性の維持**:
   - 参照パスは相対パスで統一（`mdc:../path/to/file.mdc`）
   - ファイル名は機能を明示した命名規則に従う
   - 同一情報の重複は避ける

2. **階層構造の遵守**:
   - フローは `flows/` ディレクトリに配置
   - 参照ドキュメントは `docs/` ディレクトリに配置
   - スクリプトは `scripts/` ディレクトリに配置

3. **参照と更新**:
   - 既存のMDCを参照する場合は、最新のパスを確認
   - 情報更新時は関連するMDCもすべて更新
   - 変更はMDC整合性確認フローで検証

4. **レガシー管理**:
   - 古いアプローチ（RAILやflow-phase）は参照のみに制限
   - 新規開発はマニュアル参照方式に従う
   - レガシーファイルは徐々に置き換え

5. **MDCファーストの徹底**:
   - エラーは問題解決より先に記録
   - 作業開始前にMDCファイルを作成/参照
   - PowerShellプロファイルでエラートラップを有効化
   - 定期的に未記録エラーを自動検出

## メンテナンス責任

1. MDCファイルの整合性確認: 週次
2. 未記録エラーの検出: 日次
3. PowerShellプロファイルの更新: 環境変更時
4. ツール制約の更新: エラー発生時
5. クイックリファレンスの更新: 方針変更時

---

最終更新: 2025-05-13
