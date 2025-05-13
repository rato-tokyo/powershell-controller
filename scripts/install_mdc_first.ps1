# MDCファーストアプローチインストーラー
# PowerShellプロファイルへのMDCファーストアプローチの統合を自動化します

# 管理者権限の確認
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# スクリプトのパスを取得
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mdcFirstScriptPath = Join-Path $scriptDir "mdc_first_approach.ps1"

# MDCファーストスクリプトの存在確認
if (-not (Test-Path $mdcFirstScriptPath)) {
    Write-Host "エラー: MDCファーストアプローチスクリプトが見つかりません: $mdcFirstScriptPath" -ForegroundColor Red
    Write-Host "先に mdc_first_approach.ps1 を作成してください。" -ForegroundColor Yellow
    exit 1
}

# PowerShellプロファイルディレクトリの作成（存在しない場合）
if (-not (Test-Path (Split-Path $PROFILE -Parent))) {
    try {
        New-Item -Path (Split-Path $PROFILE -Parent) -ItemType Directory -Force | Out-Null
        Write-Host "PowerShellプロファイルディレクトリを作成しました。" -ForegroundColor Green
    } catch {
        Write-Host "エラー: PowerShellプロファイルディレクトリの作成に失敗しました: $_" -ForegroundColor Red
        if (-not $isAdmin) {
            Write-Host "管理者権限で再度実行してください。" -ForegroundColor Yellow
        }
        exit 1
    }
}

# PowerShellプロファイルファイルの作成（存在しない場合）
if (-not (Test-Path $PROFILE)) {
    try {
        New-Item -Path $PROFILE -ItemType File -Force | Out-Null
        Write-Host "PowerShellプロファイルファイルを作成しました: $PROFILE" -ForegroundColor Green
    } catch {
        Write-Host "エラー: PowerShellプロファイルファイルの作成に失敗しました: $_" -ForegroundColor Red
        if (-not $isAdmin) {
            Write-Host "管理者権限で再度実行してください。" -ForegroundColor Yellow
        }
        exit 1
    }
}

# 現在のPowerShellプロファイルを確認
$profileContent = Get-Content -Path $PROFILE -Raw -ErrorAction SilentlyContinue
$mdcScriptRelativePath = "`$PSScriptRoot\" + (Resolve-Path -Relative $mdcFirstScriptPath)
$mdcImportLine = ". `"$mdcScriptRelativePath`""

# プロファイルが既に設定されているか確認
if ($profileContent -and $profileContent.Contains("mdc_first_approach.ps1")) {
    Write-Host "MDCファーストアプローチは既にPowerShellプロファイルに追加されています。" -ForegroundColor Yellow
    
    # 更新するかどうか確認
    $updateProfile = Read-Host "既存の設定を更新しますか？ (Y/N)"
    if ($updateProfile -ne "Y" -and $updateProfile -ne "y") {
        Write-Host "インストールをキャンセルしました。" -ForegroundColor Cyan
        exit 0
    }
    
    # 既存の設定を更新
    $profileContent = $profileContent -replace '\..*mdc_first_approach\.ps1.*', $mdcImportLine
    Set-Content -Path $PROFILE -Value $profileContent
    Write-Host "MDCファーストアプローチの設定を更新しました。" -ForegroundColor Green
} else {
    # 新しく追加
    $newProfileContent = if ($profileContent) {
        $profileContent.TrimEnd() + "`n`n# MDCファーストアプローチの統合`n$mdcImportLine`n"
    } else {
        "# PowerShellプロファイル`n`n# MDCファーストアプローチの統合`n$mdcImportLine`n"
    }
    
    Set-Content -Path $PROFILE -Value $newProfileContent
    Write-Host "MDCファーストアプローチをPowerShellプロファイルに追加しました。" -ForegroundColor Green
}

# 現在のPowerShellセッションにMDCファーストアプローチを読み込み
try {
    . $mdcFirstScriptPath
    Write-Host "現在のセッションにMDCファーストアプローチを読み込みました。" -ForegroundColor Green
    Write-Host @"

インストールが完了しました！
以下のコマンドが使用可能になりました:
- mdc-task <タイプ> [説明]  : MDC起点で作業開始
- mdc-error <コマンド> [説明]: エラーを記録
- mdc-ref <参照タイプ>      : MDCドキュメント参照
- mdc-update <課題> [状態]   : 課題状態を更新
- mdc-trap                  : エラートラップ有効化
- mdc-untrap                : エラートラップ無効化

次回のPowerShellセッションから自動的に読み込まれます。
"@ -ForegroundColor Cyan
} catch {
    Write-Host "警告: 現在のセッションへの読み込みに失敗しました: $_" -ForegroundColor Yellow
    Write-Host "PowerShellを再起動して変更を適用してください。" -ForegroundColor Yellow
}

# issues.mdファイルの更新（MDCファーストアプローチの導入を記録）
$issuesPath = "issues.md"
if (Test-Path $issuesPath) {
    $issueEntry = @"

**[MDC] MDCファーストアプローチの導入**
- 課題: 開発プロセスとMDC管理を統合するMDCファーストアプローチを導入
- 実装内容: 
  - PowerShellスクリプトによるMDC管理の自動化
  - エラー発生時の即時記録メカニズム
  - 作業開始時のMDC起点プロセス確立
  - プロンプトへの作業状態表示統合
- 関連MDC: `mdc_reference_index.mdc`
- ステータス: 完了
- 更新日: $(Get-Date -Format "yyyy-MM-dd")
"@
    
    Add-Content -Path $issuesPath -Value $issueEntry
    Write-Host "MDCファーストアプローチの導入をissues.mdに記録しました。" -ForegroundColor Green
} 