# 未記録エラー自動記録スクリプト
# MDCファーストアプローチの改善策として導入
# 
# 使用法:
# ./auto_mdc_error_record.ps1 [-LogPath <PowerShellログパス>] [-IssuesPath <issues.mdのパス>]

param (
    [string]$LogPath = "$env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt",
    [string]$IssuesPath = "../../issues.md"
)

# タイトルを表示
Write-Host @"
====================================================
    MDCファーストアプローチ - 未記録エラー自動記録
====================================================
"@ -ForegroundColor Cyan

# コマンド履歴ファイルの存在確認
if (-not (Test-Path $LogPath)) {
    Write-Warning "PowerShellコマンド履歴ファイルが見つかりません: $LogPath"
    exit 1
}

# issues.mdファイルの存在確認
if (-not (Test-Path $IssuesPath)) {
    Write-Warning "issues.mdファイルが見つかりません: $IssuesPath"
    exit 1
}

# コマンド履歴とエラーパターンを取得
$commandHistory = Get-Content $LogPath -Tail 1000
$issuesContent = Get-Content $IssuesPath -Raw

# エラーパターンの定義
$errorPatterns = @(
    @{
        Pattern = "Exception"
        Description = "例外エラー"
        Severity = "高"
    },
    @{
        Pattern = "Error:"
        Description = "一般エラー"
        Severity = "中"
    },
    @{
        Pattern = "Could not find"
        Description = "ファイル/パス未検出エラー"
        Severity = "中"
    },
    @{
        Pattern = "Access is denied"
        Description = "アクセス拒否エラー"
        Severity = "高"
    },
    @{
        Pattern = "OutOfRange"
        Description = "範囲外エラー"
        Severity = "中"
    },
    @{
        Pattern = "NullReference"
        Description = "Null参照エラー"
        Severity = "高"
    }
)

# 検出された未記録エラーの保存用配列
$unreportedErrors = @()

# コマンド履歴をスキャンして未記録のエラーを検出
Write-Host "コマンド履歴を分析中..." -ForegroundColor Yellow

foreach ($command in $commandHistory) {
    foreach ($errorPattern in $errorPatterns) {
        if ($command -match $errorPattern.Pattern) {
            # 抽出されたコマンドがissues.mdに既に記録されているか確認
            $isReported = $issuesContent -match [regex]::Escape($command)
            
            if (-not $isReported) {
                # 未記録の場合は配列に追加
                $unreportedErrors += [PSCustomObject]@{
                    Command = $command
                    ErrorType = $errorPattern.Description
                    Severity = $errorPattern.Severity
                }
            }
        }
    }
}

# 結果レポート
Write-Host "`n検出結果:" -ForegroundColor Green
Write-Host "解析したコマンド数: $($commandHistory.Count)" -ForegroundColor Gray
Write-Host "検出された未記録エラー数: $($unreportedErrors.Count)" -ForegroundColor $(if ($unreportedErrors.Count -gt 0) { "Red" } else { "Green" })

if ($unreportedErrors.Count -gt 0) {
    Write-Host "`n未記録のエラー一覧:" -ForegroundColor Red
    
    # ユーザー確認
    $confirmation = Read-Host "`nこれらのエラーをissues.mdに自動記録しますか？ (Y/N)"
    
    if ($confirmation -eq 'Y' -or $confirmation -eq 'y') {
        $newIssuesContent = ""
        $recordCount = 0
        
        foreach ($error in $unreportedErrors) {
            # エラーテンプレートを作成
            $errorTemplate = @"

**[PowerShell] $($error.ErrorType)**
- 問題: PowerShellコマンド実行中にエラーが発生
- 発生環境: Windows $(([System.Environment]::OSVersion.Version).ToString()), PowerShell $($PSVersionTable.PSVersion)
- 失敗コマンド: `$($error.Command)`
- 重要度: $($error.Severity)
- ステータス: 未解決
- 記録方法: 自動検出ツール
- 更新日: $(Get-Date -Format "yyyy-MM-dd")
"@
            
            # issues.mdに追記
            Add-Content -Path $IssuesPath -Value $errorTemplate
            $recordCount++
        }
        
        Write-Host "`n$recordCount 件のエラーを自動記録しました。" -ForegroundColor Green
        Write-Host "ファイル: $IssuesPath" -ForegroundColor Gray
        
        # ToolConstraints.mdcの更新を促す
        Write-Host "`nツール制約の更新:" -ForegroundColor Yellow
        Write-Host "必要に応じて tool_constraints.mdc にもエラー詳細と回避策を追記してください。" -ForegroundColor Cyan
        Write-Host "ファイル: .cursor/rules/docs/tool_constraints.mdc" -ForegroundColor Gray
    } else {
        Write-Host "`n自動記録がキャンセルされました。手動で記録する場合は mdc-error コマンドを使用してください。" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n素晴らしい！未記録のエラーは見つかりませんでした。" -ForegroundColor Green
}

# 定期実行のための手順
Write-Host "`n定期実行の設定方法:" -ForegroundColor Cyan
Write-Host "このスクリプトを定期的に実行するには、以下のコマンドを実行してください:" -ForegroundColor Gray
Write-Host "  Register-ScheduledJob -Name 'MDC未記録エラー自動記録' -ScriptBlock { & '$PSScriptRoot\auto_mdc_error_record.ps1' } -Trigger (New-JobTrigger -Weekly -DaysOfWeek Friday -At '17:00')" -ForegroundColor White

Write-Host "`n====================================================`n" -ForegroundColor Cyan 