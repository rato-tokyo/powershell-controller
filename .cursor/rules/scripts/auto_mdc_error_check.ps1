# 未記録エラー自動検出スクリプト
# MDCファーストアプローチの改善策として導入
# 
# 使用法:
# ./auto_mdc_error_check.ps1 [-LogPath <PowerShellログパス>] [-IssuesPath <issues.mdのパス>]

param (
    [string]$LogPath = "$env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt",
    [string]$IssuesPath = "../../issues.md"
)

# タイトルを表示
Write-Host @"
====================================================
    MDCファーストアプローチ - 未記録エラー検出
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
    
    $i = 1
    foreach ($error in $unreportedErrors) {
        Write-Host "`n[$i] $($error.ErrorType) (重要度: $($error.Severity))" -ForegroundColor Yellow
        Write-Host "コマンド: $($error.Command)" -ForegroundColor Gray
        
        # エラー記録コマンドの例を表示
        Write-Host "記録コマンド例:" -ForegroundColor Cyan
        Write-Host "mdc-error '$($error.Command -replace "'", "''")' '$($error.ErrorType)エラーが発生'" -ForegroundColor White
        
        $i++
    }
    
    # 集計レポート
    Write-Host "`n重要度別統計:" -ForegroundColor Magenta
    $severityCounts = $unreportedErrors | Group-Object -Property Severity | Select-Object Name, Count
    foreach ($severity in $severityCounts) {
        Write-Host "重要度 $($severity.Name): $($severity.Count)件" -ForegroundColor $(if ($severity.Name -eq "高") { "Red" } elseif ($severity.Name -eq "中") { "Yellow" } else { "Green" })
    }
    
    # 自動記録のオプションを表示
    Write-Host "`n未記録エラーの自動記録:" -ForegroundColor Cyan
    Write-Host "以下のコマンドを実行して、見つかったエラーを一括記録できます:" -ForegroundColor Gray
    Write-Host "  ./auto_mdc_error_record.ps1" -ForegroundColor White
} else {
    Write-Host "`n素晴らしい！未記録のエラーは見つかりませんでした。" -ForegroundColor Green
}

# 定期実行のための手順
Write-Host "`n定期実行の設定方法:" -ForegroundColor Cyan
Write-Host "このスクリプトを定期的に実行するには、以下のコマンドを実行してください:" -ForegroundColor Gray
Write-Host "  Register-ScheduledJob -Name 'MDC未記録エラー検出' -ScriptBlock { & '$PSScriptRoot\auto_mdc_error_check.ps1' } -Trigger (New-JobTrigger -Daily -At '10:00')" -ForegroundColor White

Write-Host "`n====================================================`n" -ForegroundColor Cyan 