# AIアシスト機能
# MDCファーストアプローチのAI支援機能統合スクリプト
#
# 使用方法:
#   & ./ai_assist.ps1 -TaskType <タイプ> -Description <説明> -MDCPath <MDCパス> [-AssistLevel <レベル>]

param (
    [Parameter(Mandatory = $true)]
    [ValidateSet("bug", "feature", "refactor", "quality", "mdc", "test")]
    [string]$TaskType,
    
    [Parameter(Mandatory = $true)]
    [string]$Description,
    
    [Parameter(Mandatory = $true)]
    [string]$MDCPath,
    
    [Parameter(Mandatory = $false)]
    [ValidateSet("mdc_only", "implementation", "full")]
    [string]$AssistLevel = "mdc_only"
)

# 現在の作業ディレクトリを取得
$workingDir = Get-Location

Write-Host "AI支援を開始します: $TaskType - $Description" -ForegroundColor Cyan
Write-Host "MDCパス: $MDCPath" -ForegroundColor Cyan
Write-Host "支援レベル: $AssistLevel" -ForegroundColor Cyan

# ハイブリッドモデルのワークフロー
switch ($AssistLevel) {
    "mdc_only" {
        # MDCの自動生成と提案のみを行う
        Write-Host "MDC生成モードで実行します..." -ForegroundColor Magenta
        
        # AIによるMDC生成（ai_mdc_generator.ps1を使用）
        $aiMDCPath = Join-Path $PSScriptRoot "ai_mdc_generator.ps1"
        if (Test-Path $aiMDCPath) {
            $tempMDCPath = Join-Path $env:TEMP "MDCFirst\ai_mdc_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
            & $aiMDCPath -TaskType $TaskType -Description $Description -OutputPath $tempMDCPath
            
            # 生成されたMDCをユーザーに表示
            if (Test-Path $tempMDCPath) {
                Write-Host "AIが以下のMDCを生成しました。参考にしてください。" -ForegroundColor Green
                Write-Host "===== AI生成MDC開始 =====" -ForegroundColor Yellow
                Get-Content $tempMDCPath | ForEach-Object { Write-Host $_ }
                Write-Host "===== AI生成MDC終了 =====" -ForegroundColor Yellow
                
                # MDCを編集する際の参考として使用するよう促す
                Write-Host "このMDCを参考に $MDCPath を編集してください。" -ForegroundColor Cyan
                Write-Host "生成されたMDCは $tempMDCPath に保存されています。" -ForegroundColor Cyan
            } else {
                Write-Warning "MDCの生成に失敗しました。手動でMDCを作成してください。"
            }
        } else {
            Write-Warning "ai_mdc_generator.ps1が見つかりません。"
            Write-Host "このスクリプトを作成して、AIによるMDC生成を有効化してください。" -ForegroundColor Yellow
        }
    }
    
    "implementation" {
        # MDC生成と実装計画の提案まで行う
        Write-Host "実装計画モードで実行します..." -ForegroundColor Magenta
        
        # 1. AIによるMDC生成
        $aiMDCPath = Join-Path $PSScriptRoot "ai_mdc_generator.ps1"
        $tempMDCPath = Join-Path $env:TEMP "MDCFirst\ai_mdc_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
        
        if (Test-Path $aiMDCPath) {
            & $aiMDCPath -TaskType $TaskType -Description $Description -OutputPath $tempMDCPath
            
            # 生成されたMDCをユーザーに表示
            if (Test-Path $tempMDCPath) {
                Write-Host "AIが以下のMDCを生成しました。参考にしてください。" -ForegroundColor Green
                Write-Host "===== AI生成MDC開始 =====" -ForegroundColor Yellow
                Get-Content $tempMDCPath | ForEach-Object { Write-Host $_ }
                Write-Host "===== AI生成MDC終了 =====" -ForegroundColor Yellow
                
                # 2. AIによる実装計画の作成
                $aiPlannerPath = Join-Path $PSScriptRoot "ai_planner.ps1"
                if (Test-Path $aiPlannerPath) {
                    # タスクタイプに応じたフェーズを決定
                    $phase = switch($TaskType) {
                        "bug" { "green" }
                        "feature" { "contract" }
                        "refactor" { "refactor" }
                        "test" { "red" }
                        default { "contract" }
                    }
                    
                    Write-Host "$phase フェーズの実装計画を作成します..." -ForegroundColor Cyan
                    & $aiPlannerPath -Phase $phase -MDCPath $tempMDCPath
                } else {
                    Write-Warning "ai_planner.ps1が見つかりません。"
                    Write-Host "このスクリプトを作成して、AIによる計画作成を有効化してください。" -ForegroundColor Yellow
                }
            } else {
                Write-Warning "MDCの生成に失敗しました。"
            }
        } else {
            Write-Warning "ai_mdc_generator.ps1が見つかりません。"
        }
    }
    
    "full" {
        # MDC生成、計画作成、実装まで全て行う
        Write-Host "フル自動モードで実行します..." -ForegroundColor Magenta
        
        # 1. AIによるMDC生成
        $aiMDCPath = Join-Path $PSScriptRoot "ai_mdc_generator.ps1"
        $tempMDCPath = Join-Path $env:TEMP "MDCFirst\ai_mdc_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
        
        if (Test-Path $aiMDCPath) {
            & $aiMDCPath -TaskType $TaskType -Description $Description -OutputPath $tempMDCPath
            
            # 2. 生成されたMDCをユーザーに表示し、承認を求める
            if (Test-Path $tempMDCPath) {
                Write-Host "AIが以下のMDCを生成しました。" -ForegroundColor Green
                Write-Host "===== AI生成MDC開始 =====" -ForegroundColor Yellow
                Get-Content $tempMDCPath | ForEach-Object { Write-Host $_ }
                Write-Host "===== AI生成MDC終了 =====" -ForegroundColor Yellow
                
                $confirmation = Read-Host "この内容でAIに実装を進めさせますか？ (Y/N)"
                if ($confirmation -eq 'Y' -or $confirmation -eq 'y') {
                    # 3. AIによる実装計画の作成と実行
                    $aiPlannerPath = Join-Path $PSScriptRoot "ai_planner.ps1"
                    if (Test-Path $aiPlannerPath) {
                        # タスクタイプに応じたフェーズを決定
                        $phases = switch($TaskType) {
                            "bug" { @("green") }
                            "feature" { @("contract", "red", "green", "document") }
                            "refactor" { @("refactor", "green") }
                            "test" { @("red", "green") }
                            default { @("contract", "red", "green", "document") }
                        }
                        
                        # 各フェーズを順番に実行
                        foreach ($phase in $phases) {
                            Write-Host "$phase フェーズを実行します..." -ForegroundColor Cyan
                            & $aiPlannerPath -Phase $phase -MDCPath $tempMDCPath -Execute
                            
                            # フェーズ完了後にユーザー確認
                            $phaseConfirmation = Read-Host "次のフェーズに進みますか？ (Y/N)"
                            if ($phaseConfirmation -ne 'Y' -and $phaseConfirmation -ne 'y') {
                                Write-Host "ユーザーの指示により処理を中断します。" -ForegroundColor Yellow
                                break
                            }
                        }
                        
                        # 全フェーズ完了通知
                        Write-Host "AIによる実装が完了しました。結果を確認してください。" -ForegroundColor Green
                        
                        # 課題の状態を更新
                        $updateCmd = "mdc-update `"$Description`" `"完了`" `"AI支援により実装完了`""
                        Write-Host "課題を更新するには以下のコマンドを実行してください:" -ForegroundColor Yellow
                        Write-Host $updateCmd -ForegroundColor Cyan
                    } else {
                        Write-Warning "ai_planner.ps1が見つかりません。"
                    }
                } else {
                    Write-Host "ユーザーにより中断されました。生成されたMDCは $tempMDCPath に保存されています。" -ForegroundColor Yellow
                }
            } else {
                Write-Warning "MDCの生成に失敗しました。"
            }
        } else {
            Write-Warning "ai_mdc_generator.ps1が見つかりません。"
        }
    }
}

Write-Host "AI支援が完了しました。" -ForegroundColor Green 