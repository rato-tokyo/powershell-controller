# MDCファーストアプローチ詳細説明 v2.0

## 目次
1. [MDCファーストアプローチとは](#MDCファーストアプローチとは)
2. [設計思想](#設計思想)
3. [ハイブリッドモデル](#ハイブリッドモデル)
4. [利点](#利点)
5. [インストールと設定](#インストールと設定)
6. [コマンド一覧](#コマンド一覧)
7. [利用シナリオ別ガイド](#利用シナリオ別ガイド)
8. [プロンプト統合](#プロンプト統合)
9. [トラブルシューティング](#トラブルシューティング)
10. [カスタマイズ方法](#カスタマイズ方法)

## MDCファーストアプローチとは

MDCファーストアプローチは、MDC（Markdown Cursor）管理を開発プロセスに統合するためのPowerShell実装です。従来の「問題発生→解決→文書化」という流れに代わり、「先に文書化、後に実装」という原則を実現します。

v2.0からは、AI支援によるハイブリッドモデルを導入し、「先にMDC、後に実装」のワークフローをAIの支援を受けながら効率的に進めることができるようになりました。

本アプローチの核となる考え方は「すべての作業はMDCから始まる」ということです。バグ修正、機能追加、リファクタリングなど、どのような作業も最初にMDCファイルを開き、作業内容を定義してから実装を始めます。AIが支援することで、この工程をさらに効率化します。

## 設計思想

MDCファーストアプローチv2.0は、以下の原則に基づいて設計されています：

### 1. MDCを起点とする開発
- すべての作業は適切なMDCファイルを開くことから始まります
- 問題解決よりも問題の記録を優先します
- 実装前にドキュメントが存在することを保証します

### 2. AIとの協働
- AIはMDC作成から実装までのさまざまな段階で支援します
- 人間の判断とAIの効率を組み合わせます
- 自動化レベルを柔軟に調整できます

### 3. シームレスな統合
- MDC操作が特別な作業ではなく、開発フローの自然な一部となるよう設計されています
- PowerShellプロンプトにMDC情報を表示し、常に現在の作業コンテキストを可視化します
- コマンド一発でMDC操作が完了するよう効率化されています

### 4. 即時記録と追跡
- エラー発生時に即座に記録できるメカニズムを提供します
- 課題の状態変化を容易に追跡・更新できます
- 自動エラー検出により記録忘れを防止します

## ハイブリッドモデル

MDCファーストアプローチv2.0では、人間とAIのハイブリッドワークフローを3つのモードで提供します：

### 1. 従来の人間主導モード
開発者がMDCを作成し、それに基づいて実装する従来のワークフローです。AIは補助的な役割にとどまります。

```
人間: MDC作成 → 人間: 仕様定義 → 人間: テスト作成 → 人間: 実装 → 人間: ドキュメント
```

### 2. AIサポートモード
開発者が主導しながらも、AIがMDC作成や実装の提案を行い、開発者がそれをレビュー・調整するモードです。

```
人間: 要件定義 → AI: MDC生成 → 人間: レビュー・調整 → AI: テスト計画 → 人間: レビュー → 人間: 実装
```

### 3. AI主導モード
AIが計画から実装までを主導し、開発者はレビューと承認を行うモードです。

```
人間: 要件定義 → AI: MDC生成 → 人間: レビュー → AI: 計画 → AI: テスト作成 → 人間: レビュー → AI: 実装 → 人間: レビュー
```

これらのモードは、作業の性質や開発者の好みに応じて柔軟に選択できます。

## 利点

MDCファーストアプローチv2.0の主な利点：

- **ドキュメント品質の向上**：作業前にドキュメントを作成するため、後付けドキュメントより正確で詳細な記録が残ります
- **問題の見落とし防止**：エラー即時記録メカニズムにより、解決を急ぐあまり記録し忘れるという事態を防ぎます
- **作業状態の可視化**：プロンプトへの課題表示により、現在取り組んでいる課題が常に意識されます
- **効率的なMDC参照**：コマンド一発で必要なMDCファイルを開けるため、参照作業が効率化されます
- **一貫性の確保**：課題の記録形式が統一され、追跡や分析が容易になります
- **AI支援による効率化**：AIによるMDC生成や実装支援により、定型的な作業が効率化されます
- **ノウハウの継承**：AIが過去のパターンを学習し、新しい開発者にも一貫した品質の作業を提供します
- **柔軟な自動化レベル**：作業の性質や緊急度に応じて、自動化レベルを柔軟に調整できます

## インストールと設定

MDCファーストアプローチは以下の方法でインストール・設定できます：

### クイックスタート（一時的に使用する場合）

```powershell
cd scripts
./quick_start.ps1
```

このコマンドを実行すると、現在のPowerShellセッションでのみMDCファーストアプローチが有効になります。セッションを終了すると設定は失われます。

### 永続的なインストール

```powershell
cd scripts
./install_mdc_first.ps1
```

このコマンドを実行すると、PowerShellプロファイルにMDCファーストアプローチが統合され、すべてのPowerShellセッションで自動的に読み込まれるようになります。

### AI支援機能の設定

AI支援機能を使用するには、`templates`ディレクトリにある以下のテンプレートファイルを編集し、AIとの連携方法を設定する必要があります：

1. `ai_assist.ps1`: AIによる作業支援の統合スクリプト
2. `ai_mdc_generator.ps1`: AIによるMDC生成スクリプト
3. `ai_planner.ps1`: AIによる実行計画作成スクリプト
4. `ai_implementer.ps1`: AIによる実装スクリプト

これらのファイルをscriptsディレクトリにコピーし、プロジェクトの要件に合わせてカスタマイズしてください。

## コマンド一覧

MDCファーストアプローチv2.0は以下のコマンドを提供します：

### 基本コマンド

#### 1. mdc-task: 作業開始

MDCファイルを起点に新しい作業を開始します。

```powershell
mdc-task <タイプ> [説明] [-AIAssist]
```

**パラメータ**:
- `タイプ`: 作業の種類（必須）
  - `bug`, `feature`, `refactor`, `quality`, `mdc`, `test`
- `説明`: 作業内容の説明（オプション）
- `-AIAssist`: AI支援を有効にするフラグ（オプション）

**実行例**:

```powershell
mdc-task feature "新しいPowerShellコマンドサポートの追加"
mdc-task bug "PSReadLineのバグ対応" -AIAssist
```

#### 2. mdc-error: エラー記録

コマンド実行時にエラーが発生した場合、即座に記録します。

```powershell
mdc-error <失敗したコマンド> [エラーの説明] [-AutoOpen]
```

#### 3. mdc-ref: MDCドキュメント参照

必要なMDCファイルを素早く参照します。

```powershell
mdc-ref <参照タイプ>
```

#### 4. mdc-update: 課題状態更新

課題の状態を更新します。

```powershell
mdc-update <課題タイトル> [ステータス] [備考]
```

#### 5. mdc-trap / mdc-untrap: エラー自動検出

エラー自動検出を有効/無効にします。

```powershell
mdc-trap    # エラートラップを有効化
mdc-untrap  # エラートラップを無効化
```

### AIハイブリッドコマンド

#### 1. mdc-ai-task: AI支援付き作業開始

```powershell
mdc-ai-task <タイプ> [説明]
# または
mdc-task <タイプ> [説明] -AIAssist
```

このコマンドは`Start-MDCTask`を`-AIAssist`フラグ付きで実行するのと同じです。AIがMDCの作成を支援します。

#### 2. mdc-ai-gen: AIによるMDC生成

AIにMDCファイルを自動生成させます。

```powershell
mdc-ai-gen <タイプ> <説明> [出力パス]
```

**実行例**:
```powershell
mdc-ai-gen feature "環境変数サポート機能の追加" "./custom_mdc.md"
```

#### 3. mdc-ai-plan: AIによる実行計画作成

AIに特定フェーズの実行計画を立てさせます。

```powershell
mdc-ai-plan <フェーズ> [MDCパス] [-Execute]
```

**パラメータ**:
- `フェーズ`: 実行するフェーズ（必須）
  - `contract`, `red`, `green`, `document`, `refactor`
- `MDCパス`: MDCファイルのパス（オプション）
- `-Execute`: 計画を自動実行するフラグ（オプション）

**実行例**:
```powershell
mdc-ai-plan red "./custom_mdc.md"  # テスト作成計画を立てる
mdc-ai-plan green -Execute  # 実装計画を立てて実行する
```

#### 4. mdc-ai-impl: AIによる実装

AIに計画に基づいた実装を行わせます。

```powershell
mdc-ai-impl <計画ファイルパス> [実行モード]
```

**パラメータ**:
- `計画ファイルパス`: AI計画ファイルのパス（必須）
- `実行モード`: 実行モード（オプション）
  - `interactive`: 各ステップを確認しながら実行（デフォルト）
  - `automatic`: 全ステップを自動実行
  - `review_only`: 計画をレビューのみ（実行なし）

**実行例**:
```powershell
mdc-ai-impl "./ai_plans/feature_plan_20240601.md" interactive
```

## 利用シナリオ別ガイド

### シナリオ1: AI支援による新機能開発

AIの支援を受けながら新機能を開発する典型的なワークフローです：

```powershell
# 1. AI支援による作業開始
mdc-ai-task feature "PowerShellコマンド実行時の環境変数サポート"

# （このタイミングでAIが生成したMDCがレビュー用に表示される）

# 2. MDCを編集し、作業内容を確定

# 3. AIにテスト計画を立てさせる
mdc-ai-plan red

# 4. 計画をレビューし、実行するかどうかを決定

# 5. AIに実装を行わせる場合
mdc-ai-plan green -Execute

# 6. 人間が実装する場合は通常のワークフローで進める

# 7. 作業完了後
mdc-update "PowerShellコマンド実行時の環境変数サポート" "完了" "PR#123でマージ済み"
```

### シナリオ2: エラー発生時のAI支援

```powershell
# 1. エラートラップを有効化
mdc-trap

# 2. エラーが発生するコマンドを実行
rm -rf temp_folder  # エラー発生

# 3. エラーを記録
mdc-error "rm -rf temp_folder" "UNIXスタイルコマンドはPowerShellで直接サポートされていない"

# 4. AIに回避策を提案してもらう
mdc-ai-task bug "UNIXスタイルコマンドの互換性問題"

# 5. AIが生成した回避策を確認し、実装
```

### シナリオ3: AI主導の完全自動モード

```powershell
# 1. AIにMDCを生成させる
mdc-ai-gen feature "ログ出力フォーマットの国際化対応"

# 2. AIによるMDCをレビュー・承認

# 3. AI主導でフェーズを実行（contract→red→green→document）
mdc-ai-plan contract -Execute
# （レビュー後）
mdc-ai-plan red -Execute
# （レビュー後）
mdc-ai-plan green -Execute
# （レビュー後）
mdc-ai-plan document -Execute

# 4. 作業完了後
mdc-update "ログ出力フォーマットの国際化対応" "完了" "AI支援により実装完了"
```

## プロンプト統合

MDCファーストアプローチは、PowerShellプロンプトを拡張して現在の作業状態を表示します：

```
[MDC:BUG] PS C:\project>
```

AI支援モードでは表示が変更され、AI支援が有効であることを示します：

```
[MDC:BUG:AI] PS C:\project>
```

## トラブルシューティング

### AI支援機能が動作しない

```
AIアシストスクリプトが見つかりません: C:\project\scripts\ai_assist.ps1
```

**解決策**:
1. `templates`ディレクトリから必要なAIスクリプトを`scripts`ディレクトリにコピーしてください
2. スクリプト内のAI API連携部分をプロジェクトに合わせてカスタマイズしてください

### AIによる生成結果が期待と異なる

**解決策**:
1. AIスクリプト内のプロンプトをより具体的なものに調整してください
2. 生成結果を手動で編集して改善してください
3. AI実装の実行モードを`interactive`に設定し、各ステップを確認しながら進めてください

## カスタマイズ方法

### AI連携方法のカスタマイズ

各AIスクリプト内の`Invoke-AIModelAPI`関数を、実際のAI API（OpenAI、Claude、Azure OpenAIなど）と連携するよう実装してください：

```powershell
function Invoke-AIModelAPI {
    param (
        [string]$Prompt,
        [string]$Model = "gpt-4",
        [int]$MaxTokens = 2000
    )
    
    # OpenAI APIの例
    $headers = @{
        "Authorization" = "Bearer $env:OPENAI_API_KEY"
        "Content-Type" = "application/json"
    }
    
    $body = @{
        "model" = $Model
        "messages" = @(
            @{
                "role" = "system"
                "content" = "あなたは開発を支援するAIアシスタントです。"
            },
            @{
                "role" = "user"
                "content" = $Prompt
            }
        )
        "max_tokens" = $MaxTokens
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "https://api.openai.com/v1/chat/completions" -Method Post -Headers $headers -Body $body
    return $response.choices[0].message.content
}
```

### 自動化レベルのカスタマイズ

`ai_assist.ps1`の`AssistLevel`パラメータを調整することで、AIの自動化レベルを変更できます：

```powershell
# AI支援レベルをデフォルトで変更
[string]$AssistLevel = "implementation"  # mdc_only → implementation に変更
```

MDCファーストアプローチv2.0は、プロジェクトの要件に合わせて自由にカスタマイズできます。AI連携方法や自動化レベルを調整し、最適な開発ワークフローを構築してください。 