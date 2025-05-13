# MDCファイル管理ガイド

## 概要
このディレクトリ（`.cursor/rules`）には、AIが利用するMDC（Markdown Cursor）ファイルが格納されています。
MDCファイルは、AIに特定の開発作業を指示するために使用されるCursorのカスタム命令機能を活用したマークダウンファイルです。
以前は「Manual Development Control」と誤って記載されていましたが、正しくは「Markdown Cursor」です。

## ディレクトリ構造

```
.cursor/rules/
├── flows/              # フローMDCファイル（チャットで実行可能）
│   ├── main/           # メインフロー（完全なフロー）
│   │   ├── requirements_change.mdc  # 仕様変更フロー
│   │   ├── issue_improvement.mdc    # 課題改善フロー
│   │   ├── code_quality.mdc         # コード品質向上フロー
│   │   └── mdc_check.mdc            # MDC整合性確認フロー
│   ├── phases/         # 個別フェーズ
│   │   ├── contract.mdc             # 契約フェーズ
│   │   ├── red.mdc                  # テスト作成フェーズ
│   │   ├── green.mdc                # 実装フェーズ
│   │   ├── document.mdc             # ドキュメントフェーズ 
│   │   └── refactor.mdc             # リファクタリングフェーズ
│   └── main.mdc        # 基本ルール（常に最初に添付）
└── docs/               # 補助的なドキュメントファイル
    ├── flow_execution.mdc  # フロー実行方法
    ├── flow_overview.mdc   # フロー概要
    ├── init.mdc            # 初期化時のルール
    ├── python_test.mdc     # Pythonテストルール
    ├── environment.mdc     # 環境設定
    ├── manual_reference.mdc # マニュアル参照方式
    ├── flow_phase.mdc      # flow-phase方針（レガシー）
    ├── rail.mdc            # RAIL方針（レガシー）
    └── main.mdc            # 基本ルール（参照用）
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
