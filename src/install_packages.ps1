# パッケージインストールスクリプト
Write-Host "分割したパッケージをインストールします..." -ForegroundColor Cyan

# カレントディレクトリを取得
$currentDir = Get-Location

try {
    # utils パッケージをインストール
    Write-Host "py_pshell_utils パッケージをインストールしています..." -ForegroundColor Yellow
    Set-Location "$currentDir\py_pshell_utils"
    pip install -e . --no-deps
    
    if ($LASTEXITCODE -ne 0) {
        throw "py_pshell_utils のインストールに失敗しました。"
    }
    
    # async パッケージをインストール
    Write-Host "py_pshell_async パッケージをインストールしています..." -ForegroundColor Yellow
    Set-Location "$currentDir\py_pshell_async"
    pip install -e . --no-deps
    
    if ($LASTEXITCODE -ne 0) {
        throw "py_pshell_async のインストールに失敗しました。"
    }
    
    # core パッケージをインストール
    Write-Host "py_pshell_core パッケージをインストールしています..." -ForegroundColor Yellow
    Set-Location "$currentDir\py_pshell_core"
    pip install -e . --no-deps
    
    if ($LASTEXITCODE -ne 0) {
        throw "py_pshell_core のインストールに失敗しました。"
    }
    
    # 元のディレクトリに戻る
    Set-Location $currentDir
    
    Write-Host "インストール完了！" -ForegroundColor Green
    Write-Host "テストを実行するには python test_packages.py を実行してください。" -ForegroundColor Green
}
catch {
    Write-Host "エラーが発生しました: $_" -ForegroundColor Red
    # 元のディレクトリに戻る
    Set-Location $currentDir
    exit 1
} 