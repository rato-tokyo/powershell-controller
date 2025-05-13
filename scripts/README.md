# MDCファーストアプローチ

## 概要
MDCファーストアプローチは、開発プロセスとMDC（Markdown Cursor）管理を統合するためのPowerShellツールセットです。MDCを起点として全ての開発作業を行い、エラー記録や課題管理を効率化します。バージョン2.0からはAIとのハイブリッドワークフローをサポートし、開発プロセスの自動化と効率化を強化しています。

## 主な特徴
- **作業の起点をMDCに一元化**: 全ての開発作業はMDCファイルを編集することから始まります
- **エラー即時記録メカニズム**: エラー発生時に簡単なコマンドで即時にissues.mdに記録できます
- **PowerShellプロンプト統合**: 現在進行中のMDC作業がプロンプトに表示されます
- **課題管理の自動化**: 課題の記録・更新がコマンド一発で行えます
- **AIハイブリッド機能**: AIによるMDC生成、実装計画、コード実装の支援機能を提供します

## インストール方法
PowerShellで以下のコマンドを実行します:

```powershell
# プロジェクトルートディレクトリで実行
cd scripts
./install_mdc_first.ps1
```

インストーラーは以下の処理を行います:
1. PowerShellプロファイルを確認・作成（必要な場合）
2. MDCファーストアプローチスクリプトをプロファイルに統合
3. 現在のセッションにMDCファーストアプローチを読み込み
4. issues.mdに導入記録を追加

## 使用方法

### 基本コマンド

#### 作業開始
MDCファイルを起点に新しい作業を開始します:

```powershell
mdc-task <タイプ> [説明]
```

利用可能なタイプ:
- `bug`: バグ修正（issue_improvement.mdc）
- `feature`: 新機能追加（requirements_change.mdc）
- `refactor`: リファクタリング（refactor.mdc）
- `quality`: コード品質向上（code_quality.mdc）
- `mdc`: MDC整合性確認（mdc_check.mdc）
- `test`: テスト追加（red.mdc）

例:
```powershell
mdc-task feature "新しいPowerShellコマンドサポートの追加"
```

#### エラー記録
コマンド実行時にエラーが発生した場合、即座に記録できます:

```powershell
mdc-error <失敗したコマンド> [エラーの説明]
```

例:
```powershell
mdc-error "rm -rf temp_folder" "UNIXスタイルコマンドの互換性問題"
```

#### MDCドキュメント参照
必要なMDCファイルを素早く参照できます:

```powershell
mdc-ref <参照タイプ>
```

利用可能な参照タイプ:
- `index`: MDC参照インデックス
- `main`: メインMDCルール
- `flow`: フロー概要
- `contract`, `red`, `green`, `document`, `refactor`: 各フェーズMDC
- `tool`: ツール制約
- `test`: テスト規約
- `environment`: 環境設定

例:
```powershell
mdc-ref tool  # tool_constraints.mdcを開く
```

#### 課題状態更新
課題の状態を更新します:

```powershell
mdc-update <課題タイトル> [ステータス] [備考]
```

利用可能なステータス:
- `進行中`（デフォルト）
- `完了`
- `未解決`
- `保留`

例:
```powershell
mdc-update "UNIXスタイルコマンドの互換性問題" "完了" "PowerShellネイティブコマンドに置き換え"
```

#### エラートラップ
エラー自動検出を有効/無効にします:

```powershell
mdc-trap    # エラートラップを有効化
mdc-untrap  # エラートラップを無効化
```

### AIハイブリッドコマンド

#### AI支援付き作業開始
AIの支援を受けながら新しい作業を開始します:

```powershell
mdc-ai-task <タイプ> [説明]
# または
mdc-task <タイプ> [説明] -AIAssist
```

例:
```powershell
mdc-ai-task feature "新しいPowerShellコマンドサポートの追加"
```

このコマンドは:
1. MDCファイルを開きます
2. AIにMDCの内容生成を依頼します
3. 生成されたMDCをレビューのために表示します

#### AIによるMDC生成
AIにMDCファイルを自動生成させます:

```powershell
mdc-ai-gen <タイプ> <説明> [出力パス]
```

例:
```powershell
mdc-ai-gen feature "環境変数サポート機能の追加" "./custom_mdc.md"
```

#### AIによる実行計画作成
AIに特定フェーズの実行計画を立てさせます:

```powershell
mdc-ai-plan <フェーズ> [MDCパス] [-Execute]
```

利用可能なフェーズ:
- `contract`: インターフェース定義
- `red`: テスト作成
- `green`: 実装
- `document`: ドキュメント作成
- `refactor`: リファクタリング

例:
```powershell
mdc-ai-plan red "./custom_mdc.md"  # テスト作成計画を立てる
mdc-ai-plan green -Execute  # 実装計画を立てて実行する
```

#### AIによる実装
AIに計画に基づいた実装を行わせます:

```powershell
mdc-ai-impl <計画ファイルパス> [実行モード]
```

利用可能な実行モード:
- `interactive`: 各ステップを確認しながら実行（デフォルト）
- `automatic`: 全ステップを自動実行
- `review_only`: 計画をレビューのみ（実行なし）

例:
```powershell
mdc-ai-impl "./ai_plans/feature_plan_20240601.md" interactive
```

## AIとのハイブリッドモデル

MDCファーストアプローチv2.0は、以下の3つの動作モードをサポートしています:

### 1. 従来の人間主導モード
開発者がMDCを作成し、それに基づいて実装を行う従来のワークフローです。

### 2. AIサポートモード
開発者が主導しながらも、AIがMDC作成や実装の提案を行い、開発者がそれをレビュー・調整するモードです:

```powershell
# AIがMDCを生成→開発者がレビュー・調整→開発者が実装
mdc-ai-gen feature "新機能の説明"
# MDCを編集後...
mdc-ai-plan red "./generated_mdc.md"  # AIがテスト計画を提案
# 計画をレビュー後...
mdc-task feature "新機能の説明"  # 通常のワークフローで実装
```

### 3. AI主導モード
AIが計画から実装までを主導し、開発者はレビューと承認を行うモードです:

```powershell
# AIがMDCを生成→開発者がレビュー→AIが計画→AIが実装→開発者が確認
mdc-ai-gen feature "新機能の説明"
# MDCをレビュー・承認後...
mdc-ai-plan red "./generated_mdc.md" -Execute  # AIがテスト作成
# テストをレビュー後...
mdc-ai-plan green -Execute  # AIが実装を行う
# 実装をレビュー後...
mdc-update "新機能の説明" "完了" "AI支援により実装完了"
```

## AI支援スクリプトの設定

AIハイブリッド機能を使用するには、以下のスクリプトを作成する必要があります:

1. `ai_assist.ps1`: AIによる作業支援の統合スクリプト
2. `ai_mdc_generator.ps1`: AIによるMDC生成スクリプト
3. `ai_planner.ps1`: AIによる実行計画作成スクリプト
4. `ai_implementer.ps1`: AIによる実装スクリプト

これらのスクリプトのテンプレートは `templates` ディレクトリにあります。プロジェクトに合わせてカスタマイズしてください。

## プロンプト統合
MDCファーストアプローチはPowerShellプロンプトを拡張し、現在進行中の課題を表示します:

```
[MDC:BUG] PS C:\project>
```

## アンインストール
PowerShellプロファイルから手動でMDCファーストアプローチの参照を削除してください:

1. `$PROFILE` ファイルをエディタで開く
2. `mdc_first_approach.ps1` を参照している行を削除
3. PowerShellを再起動

## トラブルシューティング

### スクリプトが実行できない
PowerShellの実行ポリシーを確認・変更してください:

```powershell
Get-ExecutionPolicy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### MDCファイルが見つからない
プロジェクトのMDC構造を確認してください。スクリプト内のパスがプロジェクト構造と一致していない場合は、`mdc_first_approach.ps1` を編集して正しいパスに更新してください。

### AIスクリプトが見つからない
必要なAIスクリプトが存在するか確認してください。存在しない場合は、`templates` ディレクトリからテンプレートをコピーして、必要に応じてカスタマイズしてください。

### エラートラップが機能しない
PowerShellのバージョンによっては、エラートラップの動作が異なる場合があります。`mdc-error` コマンドを手動で使用してエラーを記録してください。

## カスタマイズ
`mdc_first_approach.ps1` を編集することで、MDCファーストアプローチをプロジェクトの要件に合わせてカスタマイズできます:

- MDCファイルのパスを変更
- 新しいコマンドやショートカットを追加
- プロンプト表示形式の調整
- エラートラップの動作変更
- AI支援レベルの調整

## ライセンス
このツールセットはプロジェクト内部での使用を想定しています。 