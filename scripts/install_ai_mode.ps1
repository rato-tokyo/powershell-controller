# MDCファーストアプローチ - AI主導モード インストーラー
# AI主導モードのみをサポートするシンプル版をインストール

# 管理者権限の確認
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")) {
    Write-Warning "管理者権限で実行することをお勧めします"
    $continue = Read-Host "続行しますか？ (Y/N)"
    if ($continue -ne "Y" -and $continue -ne "y") {
        exit
    }
}

# 設定
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$ROOT_DIR = Split-Path -Parent $SCRIPT_DIR
$MDC_DIR = Join-Path $ROOT_DIR ".cursor\rules"
$TASKS_DIR = Join-Path $MDC_DIR "tasks"
$PROFILE_PATH = $PROFILE

# 必要なディレクトリの作成
Write-Host "必要なディレクトリを作成しています..." -ForegroundColor Cyan
if (-not (Test-Path $MDC_DIR)) {
    New-Item -Path $MDC_DIR -ItemType Directory -Force | Out-Null
}
if (-not (Test-Path $TASKS_DIR)) {
    New-Item -Path $TASKS_DIR -ItemType Directory -Force | Out-Null
}
if (-not (Test-Path (Split-Path -Parent $PROFILE_PATH))) {
    New-Item -Path (Split-Path -Parent $PROFILE_PATH) -ItemType Directory -Force | Out-Null
}

# スクリプトファイルのコピー
Write-Host "MDCファーストアプローチ - AI主導モードスクリプトをコピーしています..." -ForegroundColor Cyan

# mdc_ai_mode.ps1の確認とコピー
$mdcScriptSource = Join-Path $MDC_DIR "scripts\mdc_ai_mode.ps1"
$mdcScriptDest = Join-Path $SCRIPT_DIR "mdc_ai_mode.ps1"

if (-not (Test-Path $mdcScriptSource)) {
    Write-Warning "元のmdc_ai_mode.ps1が見つかりません。スクリプトディレクトリに直接作成します。"
}
else {
    Copy-Item -Path $mdcScriptSource -Destination $mdcScriptDest -Force
}

# インストール状況の確認
$isInstalled = $false
if (Test-Path $PROFILE_PATH) {
    $profileContent = Get-Content -Path $PROFILE_PATH -Raw -ErrorAction SilentlyContinue
    $isInstalled = $profileContent -match "mdc_ai_mode\.ps1"
}

# PowerShellプロファイルへの追加
if (-not $isInstalled) {
    Write-Host "PowerShellプロファイルにMDCファーストアプローチを追加しています..." -ForegroundColor Cyan
    
    # プロファイルが存在しない場合は作成
    if (-not (Test-Path $PROFILE_PATH)) {
        New-Item -Path $PROFILE_PATH -ItemType File -Force | Out-Null
    }
    
    # プロファイルに設定を追加
    $profileAddition = @"

# MDCファーストアプローチ - AI主導モード
`$mdcScriptPath = "$mdcScriptDest"
if (Test-Path `$mdcScriptPath) {
    Import-Module `$mdcScriptPath
    # 自動エラートラップ有効化
    if (Get-Command mdc-trap -ErrorAction SilentlyContinue) { 
        mdc-trap
    }
}
else {
    Write-Warning "MDCファーストアプローチスクリプトが見つかりません: `$mdcScriptPath"
}
"@
    
    Add-Content -Path $PROFILE_PATH -Value $profileAddition
    Write-Host "PowerShellプロファイルに設定を追加しました" -ForegroundColor Green
}
else {
    Write-Host "MDCファーストアプローチはすでにインストールされています" -ForegroundColor Yellow
}

# AI主導モードガイドのコピー
$guideSource = Join-Path $MDC_DIR "AI_MODE_GUIDE.md"
$guideDest = Join-Path $MDC_DIR "AI_MODE_GUIDE.md"

if (Test-Path $guideSource) {
    Copy-Item -Path $guideSource -Destination $guideDest -Force
    Write-Host "AI主導モードガイドをコピーしました" -ForegroundColor Green
}
else {
    Write-Warning "AI主導モードガイドが見つかりません: $guideSource"
}

# インストール完了メッセージ
Write-Host @"

====================================================
    MDCファーストアプローチ - AI主導モード
    インストール完了
====================================================

以下のコマンドが利用可能になりました:

- mdc-ai-task "<課題の説明>"    : AI主導タスクを開始
- mdc-ai-gen "<課題の説明>"     : 詳細なAI主導タスクテンプレートを生成
- mdc-error "<コマンド>" "<説明>" : エラーを記録
- mdc-trap                      : エラートラップを有効化（自動実行済み）
- mdc-update "<タスク>" "<状態>"  : タスク状態を更新

設定を有効にするには、PowerShellを再起動してください。
または、以下のコマンドを実行して即時に有効化できます:

    . $PROFILE

詳細なガイドは以下にあります:
$guideDest

====================================================
"@ -ForegroundColor Cyan

# 即時有効化のオプション
$immediateActivation = Read-Host "MDCファーストアプローチ - AI主導モードを今すぐ有効化しますか？ (Y/N)"
if ($immediateActivation -eq "Y" -or $immediateActivation -eq "y") {
    try {
        . $PROFILE
        Write-Host "MDCファーストアプローチ - AI主導モードが有効化されました" -ForegroundColor Green
    }
    catch {
        Write-Warning "プロファイルの読み込み中にエラーが発生しました: $_"
        Write-Host "PowerShellを再起動して設定を有効化してください" -ForegroundColor Yellow
    }
}
else {
    Write-Host "PowerShellを再起動して設定を有効化してください" -ForegroundColor Yellow
}
