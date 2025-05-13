# MDCファーストアプローチ クイックスタート
# このスクリプトは現在のセッションですぐにMDCファーストアプローチを使い始めるためのものです

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
    
    # MDC参照インデックスを開く
    Write-Host "MDC参照インデックスを開きます..." -ForegroundColor Cyan
    mdc-ref index
    
    Write-Host @"
    
========================================================
 MDCファーストアプローチ クイックスタート
========================================================
 現在のセッションで以下のコマンドが使用可能になりました:
 
 1. 作業開始:
    mdc-task bug "バグの説明"
    mdc-task feature "新機能の説明"
    mdc-task refactor "リファクタリングの説明"
    
 2. エラー記録:
    mdc-error "失敗したコマンド" "エラーの説明"
    
 3. MDC参照:
    mdc-ref tool  # ツール制約を参照
    mdc-ref index # インデックスを参照
    
 4. 課題状態更新:
    mdc-update "課題タイトル" "進行中"
    mdc-update "課題タイトル" "完了" "完了内容の備考"
    
 5. エラートラップ:
    mdc-trap    # エラー自動検出を有効化
    mdc-untrap  # エラー自動検出を無効化
    
 MDCファーストアプローチを継続的に使用するには:
 ./install_mdc_first.ps1
========================================================
"@ -ForegroundColor Cyan

    # エラートラップを有効化
    Write-Host "エラートラップを有効化しますか？ (Y/N)" -ForegroundColor Yellow
    $enableTrap = Read-Host
    
    if ($enableTrap -eq "Y" -or $enableTrap -eq "y") {
        mdc-trap
    } else {
        Write-Host "エラートラップは無効のままです。必要なときに mdc-trap コマンドで有効化できます。" -ForegroundColor Yellow
    }
    
    # 使用例の提示
    Write-Host @"
    
[使用例]
1. バグ修正を開始:
   mdc-task bug "PSReadLineモジュールのバグ対応"

2. エラーを記録:
   mdc-error "rm -rf folder" "UNIXスタイルコマンドの互換性問題"

3. 課題状態を更新:
   mdc-update "PSReadLineモジュールのバグ対応" "進行中" "原因調査中"
   
詳細なドキュメントは ./README.md を参照してください。
"@ -ForegroundColor Green

} catch {
    Write-Host "エラー: MDCファーストアプローチの読み込みに失敗しました: $_" -ForegroundColor Red
    exit 1
} 