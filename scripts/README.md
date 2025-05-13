# MDCファーストアプローチ

## 概要
MDCファーストアプローチは、開発プロセスとMDC（Markdown Cursor）管理を統合するためのPowerShellツールセットです。MDCを起点として全ての開発作業を行い、エラー記録や課題管理を効率化します。

## 主な特徴
- **作業の起点をMDCに一元化**: 全ての開発作業はMDCファイルを編集することから始まります
- **エラー即時記録メカニズム**: エラー発生時に簡単なコマンドで即時にissues.mdに記録できます
- **PowerShellプロンプト統合**: 現在進行中のMDC作業がプロンプトに表示されます
- **課題管理の自動化**: 課題の記録・更新がコマンド一発で行えます

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

### 作業開始
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

### エラー記録
コマンド実行時にエラーが発生した場合、即座に記録できます:

```powershell
mdc-error <失敗したコマンド> [エラーの説明]
```

例:
```powershell
mdc-error "rm -rf temp_folder" "UNIXスタイルコマンドの互換性問題"
```

### MDCドキュメント参照
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

### 課題状態更新
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

### エラートラップ
エラー自動検出を有効/無効にします:

```powershell
mdc-trap    # エラートラップを有効化
mdc-untrap  # エラートラップを無効化
```

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

### エラートラップが機能しない
PowerShellのバージョンによっては、エラートラップの動作が異なる場合があります。`mdc-error` コマンドを手動で使用してエラーを記録してください。

## カスタマイズ
`mdc_first_approach.ps1` を編集することで、MDCファーストアプローチをプロジェクトの要件に合わせてカスタマイズできます:

- MDCファイルのパスを変更
- 新しいコマンドやショートカットを追加
- プロンプト表示形式の調整
- エラートラップの動作変更

## ライセンス
このツールセットはプロジェクト内部での使用を想定しています。 