# MDCファーストアプローチ デモスクリプト
# このスクリプトはMDCファーストアプローチの機能をデモンストレーションします

# スクリプトのパスを取得
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mdcFirstScriptPath = Join-Path $scriptDir "mdc_first_approach.ps1"

# MDCファーストスクリプトの存在確認
if (-not (Test-Path $mdcFirstScriptPath)) {
    Write-Host "エラー: MDCファーストアプローチスクリプトが見つかりません: $mdcFirstScriptPath" -ForegroundColor Red
    exit 1
}

# 現在のセッションにMDCファーストアプローチを読み込み
try {
    . $mdcFirstScriptPath
    
    Write-Host @"
========================================================
 MDCファーストアプローチ デモ
========================================================
このデモでは、MDCファーストアプローチの主要機能を実際に使って体験します。
"@ -ForegroundColor Cyan
    
    # ステップ1: 新しい作業を開始
    Write-Host "`n[ステップ1] 新しい作業を開始します" -ForegroundColor Green
    Write-Host "作業タイプ: feature"
    Write-Host "作業内容: 「デモ機能のサポート追加」"
    Write-Host "mdc-task feature 'デモ機能のサポート追加' コマンドを実行します..."
    
    # 実際には実行せず、代わりにシミュレート
    Write-Host @"
【MDCファースト】feature タイプの作業を .cursor/rules/flows/main/requirements_change.mdc から開始します
MDCファイルを編集し、作業内容を定義した後で実装を開始してください。
エラーが発生した場合は Record-MDCError コマンドを使用してください。
課題を issues.md に記録しました。
"@ -ForegroundColor DarkCyan
    
    # ステップ2: エラーの記録
    Write-Host "`n[ステップ2] エラー発生時の記録をシミュレートします" -ForegroundColor Green
    Write-Host "エラーが発生した場合、mdc-error コマンドで即座に記録できます："
    Write-Host "mdc-error 'rm -rf temp_dir' 'UNIXコマンドの互換性問題' コマンドを実行します..."
    
    # 実際には実行せず、代わりにシミュレート
    Write-Host @"
エラーを issues.md に記録しました。
tool_constraints.mdc にも同様のエラーと回避策を記録してください。
"@ -ForegroundColor DarkCyan
    
    # ステップ3: MDCファイルの参照
    Write-Host "`n[ステップ3] MDCファイルを参照します" -ForegroundColor Green
    Write-Host "mdc-ref コマンドを使って、必要なMDCファイルを素早く参照できます："
    Write-Host "mdc-ref tool コマンドを実行します..."
    
    # 実際には実行せず、代わりにシミュレート
    Write-Host @"
【MDC参照】tool タイプのMDCファイルを開きました
"@ -ForegroundColor DarkCyan
    
    # ステップ4: 課題状態の更新
    Write-Host "`n[ステップ4] 課題状態を更新します" -ForegroundColor Green
    Write-Host "作業が進行中または完了した場合、課題の状態を更新できます："
    Write-Host "mdc-update 'デモ機能のサポート追加' '進行中' '実装中' コマンドを実行します..."
    
    # 実際には実行せず、代わりにシミュレート
    Write-Host @"
「デモ機能のサポート追加」の課題を更新しました。ステータス: 進行中
"@ -ForegroundColor DarkCyan
    
    # ステップ5: エラートラップの有効化
    Write-Host "`n[ステップ5] エラートラップを有効化します" -ForegroundColor Green
    Write-Host "エラーが発生した際に自動的に検出・通知するトラップを有効化できます："
    Write-Host "mdc-trap コマンドを実行します..."
    
    # 実際には実行せず、代わりにシミュレート
    Write-Host @"
MDCファーストエラートラップが有効になりました。エラー発生時に記録手順が表示されます。
"@ -ForegroundColor DarkCyan
    
    # エラーシミュレーション
    Write-Host "`n[ステップ6] エラーが発生した場合の動作をシミュレートします" -ForegroundColor Green
    Write-Host "エラーが発生すると以下のような情報が表示されます："
    
    # エラーのシミュレーション
    Write-Host @"
エラーが発生しました！
コマンド: Remove-Item -Recurse -Force temp_folder | rm -rf temp_folder
エラー: A parameter cannot be found that matches parameter name 'rf'.
Record-MDCError コマンドでこのエラーを記録できます:
Record-MDCError -FailedCommand 'Remove-Item -Recurse -Force temp_folder | rm -rf temp_folder' -Description 'エラーの説明'
"@ -ForegroundColor Red
    
    # デモの終了
    Write-Host "`n[デモ完了] MDCファーストアプローチの基本機能をデモンストレーションしました" -ForegroundColor Green
    Write-Host @"
MDCファーストアプローチを実際に使用するには：

1. クイックスタート（今回のセッションのみ）：
   ./quick_start.ps1

2. 継続的な使用（PowerShellプロファイルに統合）：
   ./install_mdc_first.ps1

詳細な使い方は README.md を参照してください。
"@ -ForegroundColor Cyan
    
} catch {
    Write-Host "エラー: MDCファーストアプローチの読み込みに失敗しました: $_" -ForegroundColor Red
    exit 1
} 