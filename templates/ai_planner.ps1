# AI実行計画機能
# MDCに基づいて実行計画を作成するスクリプト
#
# 使用方法:
#   & ./ai_planner.ps1 -Phase <フェーズ> [-MDCPath <MDCパス>] [-Execute]

param (
    [Parameter(Mandatory = $true)]
    [ValidateSet("contract", "red", "green", "document", "refactor")]
    [string]$Phase,
    
    [Parameter(Mandatory = $false)]
    [string]$MDCPath = "",
    
    [Parameter(Mandatory = $false)]
    [switch]$Execute = $false
)

# 現在の作業ディレクトリを取得
$workingDir = Get-Location

# MDCパスが指定されていない場合、最新のMDCを探す
if ([string]::IsNullOrEmpty($MDCPath)) {
    $tempFolder = Join-Path $env:TEMP "MDCFirst"
    if (Test-Path $tempFolder) {
        $mdcFiles = Get-ChildItem -Path $tempFolder -Filter "ai_generated_mdc_*.md" | Sort-Object LastWriteTime -Descending
        if ($mdcFiles.Count -gt 0) {
            $MDCPath = $mdcFiles[0].FullName
            Write-Host "最新のMDCを使用します: $MDCPath" -ForegroundColor Cyan
        }
    }
    
    if ([string]::IsNullOrEmpty($MDCPath)) {
        Write-Error "MDCパスが指定されておらず、最新のMDCも見つかりませんでした。"
        return
    }
}

# 計画ファイルのパスを設定
$plansFolder = Join-Path $workingDir "ai_plans"
if (-not (Test-Path $plansFolder)) {
    New-Item -Path $plansFolder -ItemType Directory | Out-Null
}
$planFile = Join-Path $plansFolder "$Phase`_plan_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"

Write-Host "実行計画の作成を開始します: フェーズ=$Phase, MDC=$MDCPath" -ForegroundColor Cyan
Write-Host "計画ファイル: $planFile" -ForegroundColor Cyan

# カスタマイズポイント: AIモデルへの接続方法を実装
function Invoke-AIModelAPI {
    param (
        [string]$Prompt,
        [string]$Model = "gpt-4",
        [int]$MaxTokens = 2000
    )
    
    # ここに実際のAI API呼び出しコードを追加
    # 例: OpenAI GPT API、Claude API、Azure OpenAI API など
    
    # テスト用のダミー実装（実際の実装に置き換えてください）
    Write-Host "AI APIを呼び出し中..." -ForegroundColor Magenta
    
    # ===== カスタマイズ開始 =====
    # 以下のコードを実際のAPI呼び出しに置き換えてください
    
    # MDCの内容を読み込む
    $mdcContent = ""
    if (Test-Path $MDCPath) {
        $mdcContent = Get-Content -Path $MDCPath -Raw
    } else {
        $mdcContent = "MDCファイルが見つかりません。"
    }
    
    # フェーズ別のテンプレート
    $taskDescription = $mdcContent -match "## .*概要" -replace "## .*概要", "" -replace "\n.*", ""
    $taskDescription = $taskDescription.Trim()
    if ([string]::IsNullOrEmpty($taskDescription)) {
        $taskDescription = "未指定のタスク"
    }
    
    $dummyResponse = "# $Phase フェーズ実行計画: $taskDescription`n`n"
    
    switch ($Phase) {
        "contract" {
            $dummyResponse += @"
## 契約フェーズの目標
インターフェース設計と契約の定義を行い、機能の境界を明確にする。

## 実行ステップ
1. **要件の分析**
   - MDCから機能要件を抽出
   - 関連する既存インターフェースの特定

2. **インターフェース設計**
   - 以下のファイルに新しいインターフェースを定義
     ```
     src/interfaces/new_feature_interface.py
     ```
   - メソッドシグネチャと入出力型の定義

3. **スタブ実装**
   - 基本的なスタブ実装の作成
     ```
     src/implementation/new_feature_stub.py
     ```
   - インターフェースに準拠した最小限の実装

4. **インターフェーステスト**
   - インターフェース検証用の最小テスト
     ```
     tests/interface/test_new_feature_interface.py
     ```

## 成功基準
- インターフェース定義が完成している
- スタブ実装が動作する
- インターフェーステストが存在する

## 次のフェーズへの入力
- 定義されたインターフェース
- スタブ実装
- 基本テスト
"@
        }
        "red" {
            $dummyResponse += @"
## レッドフェーズの目標
機能の振る舞いを定義するテストを作成し、機能実装の方向性を示す。

## 実行ステップ
1. **テスト計画**
   - テストケースの洗い出し
   - テストの優先順位付け

2. **テスト環境準備**
   - 必要なモックオブジェクトの定義
   - テストフィクスチャーの作成

3. **テスト実装**
   - 基本機能テスト
     ```
     tests/unit/test_basic_functionality.py
     ```
   - エッジケーステスト
     ```
     tests/unit/test_edge_cases.py
     ```
   - エラー処理テスト
     ```
     tests/unit/test_error_handling.py
     ```

4. **テスト実行**
   - すべてのテストを実行して失敗することを確認
   - テストカバレッジの確認

## 成功基準
- すべての要件に対応するテストが存在する
- テストは現時点では失敗する
- テストコードの品質が高い

## 次のフェーズへの入力
- テストスイート
- 期待される動作の明確な定義
"@
        }
        "green" {
            $dummyResponse += @"
## グリーンフェーズの目標
レッドフェーズで作成したテストが成功するように機能を実装する。

## 実行ステップ
1. **実装計画**
   - アーキテクチャの詳細設計
   - 依存関係の特定

2. **コア機能実装**
   - 基本機能の実装
     ```
     src/implementation/core_functionality.py
     ```
   - 内部モジュールの実装
     ```
     src/implementation/internal_modules.py
     ```

3. **エラー処理実装**
   - 例外処理とエラーハンドリング
     ```
     src/implementation/error_handling.py
     ```

4. **統合**
   - 各モジュールの統合
     ```
     src/implementation/integration.py
     ```

5. **テスト実行**
   - 単体テストの実行
   - 統合テストの実行
   - すべてのテストが成功することを確認

## 成功基準
- すべてのテストが成功する
- コードの品質が高い
- パフォーマンス要件を満たしている

## 次のフェーズへの入力
- 完全な実装コード
- 成功するテスト結果
"@
        }
        "document" {
            $dummyResponse += @"
## ドキュメントフェーズの目標
実装した機能のドキュメントを作成し、使用方法を明確にする。

## 実行ステップ
1. **APIドキュメント作成**
   - インターフェースのドキュメント
     ```
     docs/api/interface_documentation.md
     ```
   - メソッド仕様の詳細化

2. **使用例作成**
   - サンプルコード
     ```
     docs/examples/usage_examples.md
     ```
   - 実際のユースケース

3. **内部設計ドキュメント**
   - アーキテクチャ概要
     ```
     docs/design/architecture.md
     ```
   - モジュール間の関係

4. **README更新**
   - 新機能の概要をREADMEに追加
     ```
     README.md
     ```

## 成功基準
- ドキュメントが完全かつ正確
- 使用例が実行可能
- READMEが更新されている

## 次のフェーズへの入力
- 完全なドキュメントセット
"@
        }
        "refactor" {
            $dummyResponse += @"
## リファクタリングフェーズの目標
コードの品質と保守性を向上させるためのリファクタリングを行う。

## 実行ステップ
1. **コード分析**
   - 複雑度の高い部分の特定
   - 重複コードの特定
   - パフォーマンスボトルネックの特定

2. **リファクタリング計画**
   - 改善対象の優先順位付け
   - リファクタリング手法の選定

3. **テスト確認**
   - 既存テストの網羅性確認
   - 必要に応じてテスト強化

4. **コードリファクタリング**
   - モジュール分割
     ```
     src/implementation/refactored_module.py
     ```
   - パターン適用
     ```
     src/implementation/pattern_implementation.py
     ```
   - コード最適化
     ```
     src/implementation/optimized_code.py
     ```

5. **テスト実行**
   - すべてのテストが成功することを確認
   - パフォーマンステスト実行

## 成功基準
- テストがすべて成功する
- コードの品質メトリクスが向上している
- パフォーマンスが維持または向上している

## 次のフェーズへの入力
- リファクタリングされたコード
- 品質メトリクスレポート
"@
        }
    }
    
    # ===== カスタマイズ終了 =====
    
    return $dummyResponse
}

# MDCの内容を読み込む
$mdcContent = ""
if (Test-Path $MDCPath) {
    $mdcContent = Get-Content -Path $MDCPath -Raw
    Write-Host "MDCの内容を読み込みました。" -ForegroundColor Green
} else {
    Write-Warning "MDCファイルが見つかりません: $MDCPath"
    $mdcContent = "MDCファイルが見つかりません。一般的な$Phaseフェーズの計画を生成します。"
}

# AIに実行計画を生成させる
$prompt = @"
以下のMDCファイルに基づいて、$Phaseフェーズの詳細な実行計画を生成してください:

$mdcContent

実行計画には以下の情報を含めてください:
- フェーズの目標
- 詳細な実行ステップ（ファイルパスや具体的なコード変更を含む）
- 成功基準
- 次のフェーズへの入力
"@

try {
    # AIモデルAPIを呼び出して実行計画を生成
    $generatedPlan = Invoke-AIModelAPI -Prompt $prompt
    
    # 生成された計画をファイルに保存
    Set-Content -Path $planFile -Value $generatedPlan -Encoding UTF8
    
    Write-Host "実行計画の生成が完了しました: $planFile" -ForegroundColor Green
    
    # 計画の内容を表示
    Write-Host "`n===== 実行計画開始 =====" -ForegroundColor Yellow
    Get-Content $planFile | ForEach-Object { Write-Host $_ }
    Write-Host "===== 実行計画終了 =====" -ForegroundColor Yellow
    
    # Executeフラグが有効な場合は計画を実行
    if ($Execute) {
        Write-Host "`n計画の実行を開始します..." -ForegroundColor Magenta
        
        # AI実装スクリプトのパスを特定
        $aiImplementerPath = Join-Path $PSScriptRoot "ai_implementer.ps1"
        if (Test-Path $aiImplementerPath) {
            # 実装スクリプトを実行
            & $aiImplementerPath -PlanPath $planFile -Mode "interactive"
        } else {
            Write-Warning "ai_implementer.ps1が見つかりません。計画の実行はスキップされます。"
            Write-Host "このスクリプトを作成して、AIによる実装を有効化してください。" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`n計画の実行をスキップします。手動で実行する場合は以下のコマンドを使用してください:" -ForegroundColor Cyan
        Write-Host "& ./ai_implementer.ps1 -PlanPath `"$planFile`" -Mode `"interactive`"" -ForegroundColor Yellow
    }
    
    return $planFile
} catch {
    Write-Error "実行計画の生成中にエラーが発生しました: $_"
    return $null
} 