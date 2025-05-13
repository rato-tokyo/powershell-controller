# AI MDC生成機能
# MDCファイルを自動生成するスクリプト
#
# 使用方法:
#   & ./ai_mdc_generator.ps1 -TaskType <タイプ> -Description <説明> [-OutputPath <出力パス>]

param (
    [Parameter(Mandatory = $true)]
    [ValidateSet("bug", "feature", "refactor", "quality", "mdc", "test")]
    [string]$TaskType,
    
    [Parameter(Mandatory = $true)]
    [string]$Description,
    
    [Parameter(Mandatory = $false)]
    [string]$OutputPath = ""
)

# 出力パスが指定されていない場合、一時ファイルを作成
if ([string]::IsNullOrEmpty($OutputPath)) {
    $tempFolder = Join-Path $env:TEMP "MDCFirst"
    if (-not (Test-Path $tempFolder)) {
        New-Item -Path $tempFolder -ItemType Directory | Out-Null
    }
    $OutputPath = Join-Path $tempFolder "ai_generated_mdc_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
}

Write-Host "MDC生成を開始します: $TaskType - $Description" -ForegroundColor Cyan
Write-Host "出力パス: $OutputPath" -ForegroundColor Cyan

# カスタマイズポイント: AIモデルへの接続方法を実装
# ここでは例としてHTTP APIを呼び出す方法を示していますが、
# 実際のプロジェクトに合わせてカスタマイズしてください

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
    
    # ダミーの応答を返す
    $dummyResponse = "# $TaskType: $Description`n`n"
    
    # タスクタイプ別のテンプレート
    switch ($TaskType) {
        "bug" {
            $dummyResponse += @"
## バグの概要
- 問題: $Description
- 影響範囲: 要調査
- 再現手順: 未確認

## 原因分析
- 推測される原因:
  - コードの問題点
  - 環境の問題点

## 修正計画
1. バグの再現確認
2. 原因の特定
3. 修正実装
4. テスト追加
5. ドキュメント更新

## 検証方法
- 修正後にバグが解消されることを確認する手順

## 影響調査
- 修正による影響範囲
- 関連コンポーネント
"@
        }
        "feature" {
            $dummyResponse += @"
## 機能概要
- 目的: $Description
- 優先度: 中
- 期待される動作: 

## 要件定義
- 機能要件:
  - 要件1
  - 要件2
- 非機能要件:
  - パフォーマンス
  - セキュリティ

## 設計
- アーキテクチャ:
- インターフェース:
- データモデル:

## 実装計画
1. フェーズ1: インターフェース定義
2. フェーズ2: テスト作成
3. フェーズ3: 実装
4. フェーズ4: ドキュメント作成

## テスト計画
- 単体テスト
- 統合テスト
- 受け入れテスト

## ドキュメント要件
- ユーザーマニュアル
- API仕様
"@
        }
        "refactor" {
            $dummyResponse += @"
## リファクタリング目的
- 改善点: $Description
- 現状の問題:
- 期待される改善効果:

## 対象範囲
- コンポーネント:
- モジュール:
- ファイル:

## リファクタリング計画
1. 現状コードの分析
2. リファクタリング方針の決定
3. テスト作成/確認
4. リファクタリング実施
5. テスト実行による検証

## 検証方法
- 既存機能が維持されていることを確認するテスト
- パフォーマンス測定（該当する場合）

## リスク分析
- 潜在的なリスク
- 回避策
"@
        }
        default {
            $dummyResponse += @"
## 作業概要
- 内容: $Description
- 目的:
- 期待される成果:

## 実施計画
1. 現状分析
2. 方針決定
3. 実装
4. テスト
5. ドキュメント更新

## 検証方法
- 検証項目
- 成功基準

## 備考
- 特記事項
"@
        }
    }
    
    # ===== カスタマイズ終了 =====
    
    return $dummyResponse
}

# AIにMDCを生成させる
$prompt = @"
以下のタスクに対するMDCファイル(Markdown Cursor)を生成してください:
タイプ: $TaskType
説明: $Description

MDCファイルには以下の情報を含めてください:
- タスクの概要と目的
- 要件または問題の詳細
- 実施計画（フェーズ別のステップ）
- 検証方法
- 成功基準
"@

try {
    # AIモデルAPIを呼び出してMDCを生成
    $generatedMDC = Invoke-AIModelAPI -Prompt $prompt
    
    # 生成されたMDCをファイルに保存
    Set-Content -Path $OutputPath -Value $generatedMDC -Encoding UTF8
    
    Write-Host "MDCの生成が完了しました: $OutputPath" -ForegroundColor Green
    return $OutputPath
} catch {
    Write-Error "MDC生成中にエラーが発生しました: $_"
    return $null
} 