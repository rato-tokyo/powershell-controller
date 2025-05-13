# MDCファーストアプローチ実装スクリプト
# PowerShell 7環境用MDC統合管理システム
# 
# 使用方法:
# 1. このスクリプトをPowerShellプロファイルに読み込む:
#    Add-Content -Path $PROFILE -Value '. "$PSScriptRoot\mdc_first_approach.ps1"'
# 2. PowerShellを再起動するか、プロファイルを再読み込み:
#    . $PROFILE

#region MDCファースト関数群
function Start-MDCTask {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0, Mandatory = $true)]
        [ValidateSet("bug", "feature", "refactor", "quality", "mdc", "test")]
        [string]$TaskType,
        
        [Parameter(Position = 1, Mandatory = $false)]
        [string]$Description = ""
    )
    
    # 作業タイプに応じたMDCテンプレートパスを決定
    $mdcPath = switch($TaskType) {
        "bug" { ".cursor/rules/flows/main/issue_improvement.mdc" }
        "feature" { ".cursor/rules/flows/main/requirements_change.mdc" }
        "refactor" { ".cursor/rules/flows/phases/refactor.mdc" }
        "quality" { ".cursor/rules/flows/main/code_quality.mdc" }
        "mdc" { ".cursor/rules/flows/main/mdc_check.mdc" }
        "test" { ".cursor/rules/flows/phases/red.mdc" }
        default { ".cursor/rules/mdc_reference_index.mdc" }
    }
    
    # 指定されたMDCファイルが存在するか確認
    if (-not (Test-Path $mdcPath)) {
        Write-Warning "指定されたMDCファイルが見つかりません: $mdcPath"
        Write-Host "mdc_reference_index.mdcを代わりに開きます..."
        $mdcPath = ".cursor/rules/mdc_reference_index.mdc"
    }
    
    # MDCファイルをエディタで開く
    try {
        # VSCodeがインストールされていれば使用
        if (Get-Command code -ErrorAction SilentlyContinue) {
            code $mdcPath
            
            # 作業内容の説明がある場合は、issues.mdに新しい課題として追記
            if (-not [string]::IsNullOrEmpty($Description)) {
                $issueTemplate = @"
**[$($TaskType.ToUpper())] $Description**
- 課題: $Description
- 開始日: $(Get-Date -Format "yyyy-MM-dd")
- 関連MDC: `$mdcPath`
- ステータス: 作業開始
- 更新日: $(Get-Date -Format "yyyy-MM-dd")
"@
                Add-Content -Path "issues.md" -Value "`n$issueTemplate"
                Write-Host "課題を issues.md に記録しました。" -ForegroundColor Green
            }
        } else {
            # VSCodeがない場合は、利用可能なエディタで開く
            Write-Warning "VSCodeが見つかりません。デフォルトのテキストエディタで開きます。"
            Invoke-Item $mdcPath
        }
    } catch {
        Write-Error "MDCファイルを開く際にエラーが発生しました: $_"
        return
    }
    
    # MDCの読み込み完了メッセージ
    Write-Host "【MDCファースト】$TaskType タイプの作業を $mdcPath から開始します" -ForegroundColor Cyan
    Write-Host "MDCファイルを編集し、作業内容を定義した後で実装を開始してください。" -ForegroundColor Cyan
    Write-Host "エラーが発生した場合は Record-MDCError コマンドを使用してください。" -ForegroundColor Yellow
}

function Record-MDCError {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0, Mandatory = $true)]
        [string]$FailedCommand,
        
        [Parameter(Position = 1, Mandatory = $false)]
        [string]$Description = "発生したエラーの簡単な説明",
        
        [Parameter(Position = 2, Mandatory = $false)]
        [switch]$AutoOpen = $true
    )
    
    # エラー情報をissues.mdに記録
    $errorRecord = @"

**[PowerShell] コマンド実行エラー**
- 問題: $Description
- 発生環境: Windows $(([System.Environment]::OSVersion.Version).ToString()), PowerShell $($PSVersionTable.PSVersion)
- 失敗コマンド: `$FailedCommand`
- エラーメッセージ: `$($Error[0].Exception.Message)`
- ステータス: 未解決
- 更新日: $(Get-Date -Format "yyyy-MM-dd")
"@
    
    Add-Content -Path "issues.md" -Value $errorRecord
    
    # エラー記録後、関連MDCを自動的に開く（オプション）
    if ($AutoOpen) {
        if (Get-Command code -ErrorAction SilentlyContinue) {
            code ".cursor/rules/docs/tool_constraints.mdc"
        } else {
            Invoke-Item ".cursor/rules/docs/tool_constraints.mdc"
        }
    }
    
    Write-Host "エラーを issues.md に記録しました。" -ForegroundColor Green
    Write-Host "tool_constraints.mdc にも同様のエラーと回避策を記録してください。" -ForegroundColor Yellow
}

function Open-MDCReference {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0, Mandatory = $false)]
        [ValidateSet(
            "index", "main", "flow", "contract", "red", "green", 
            "document", "refactor", "tool", "test", "environment"
        )]
        [string]$ReferenceType = "index"
    )
    
    # 参照タイプに応じたMDCパスを決定
    $mdcPath = switch($ReferenceType) {
        "index" { ".cursor/rules/mdc_reference_index.mdc" }
        "main" { ".cursor/rules/flows/main.mdc" }
        "flow" { ".cursor/rules/flow_overview.mdc" }
        "contract" { ".cursor/rules/flows/phases/contract.mdc" }
        "red" { ".cursor/rules/flows/phases/red.mdc" }
        "green" { ".cursor/rules/flows/phases/green.mdc" }
        "document" { ".cursor/rules/flows/phases/document.mdc" }
        "refactor" { ".cursor/rules/flows/phases/refactor.mdc" }
        "tool" { ".cursor/rules/docs/tool_constraints.mdc" }
        "test" { ".cursor/rules/python_test.mdc" }
        "environment" { ".cursor/rules/environment.mdc" }
        default { ".cursor/rules/mdc_reference_index.mdc" }
    }
    
    # 指定されたMDCファイルが存在するか確認
    if (-not (Test-Path $mdcPath)) {
        Write-Warning "指定されたMDCファイルが見つかりません: $mdcPath"
        Write-Host "mdc_reference_index.mdcを代わりに開きます..."
        $mdcPath = ".cursor/rules/mdc_reference_index.mdc"
    }
    
    # MDCファイルをエディタで開く
    try {
        if (Get-Command code -ErrorAction SilentlyContinue) {
            code $mdcPath
        } else {
            Invoke-Item $mdcPath
        }
        Write-Host "【MDC参照】$ReferenceType タイプのMDCファイルを開きました" -ForegroundColor Cyan
    } catch {
        Write-Error "MDCファイルを開く際にエラーが発生しました: $_"
    }
}

function Update-MDCRecord {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0, Mandatory = $true)]
        [string]$IssueTitle,
        
        [Parameter(Position = 1, Mandatory = $false)]
        [ValidateSet("進行中", "完了", "未解決", "保留")]
        [string]$Status = "進行中",
        
        [Parameter(Position = 2, Mandatory = $false)]
        [string]$Notes = ""
    )
    
    # issues.mdファイルを読み込む
    $issuesContent = Get-Content -Path "issues.md" -Raw
    
    # 指定されたタイトルの課題を検索
    $pattern = "(?ms)\*\*\[[^\]]+\]\s*$([regex]::Escape($IssueTitle))\*\*.*?(?=\n\n\d+\.|$)"
    $match = [regex]::Match($issuesContent, $pattern)
    
    if ($match.Success) {
        $issueText = $match.Value
        
        # ステータスを更新
        $updatedIssue = $issueText -replace "- ステータス: .*", "- ステータス: $Status"
        
        # 更新日を更新
        $updatedIssue = $updatedIssue -replace "- 更新日: .*", "- 更新日: $(Get-Date -Format "yyyy-MM-dd")"
        
        # 追加のノートがあれば追記
        if (-not [string]::IsNullOrEmpty($Notes)) {
            if ($updatedIssue -match "- 備考:") {
                $updatedIssue = $updatedIssue -replace "- 備考: .*", "- 備考: $Notes"
            } else {
                $updatedIssue += "`n- 備考: $Notes"
            }
        }
        
        # 更新した内容をissues.mdに反映
        $updatedContent = $issuesContent.Replace($issueText, $updatedIssue)
        Set-Content -Path "issues.md" -Value $updatedContent
        
        Write-Host "「$IssueTitle」の課題を更新しました。ステータス: $Status" -ForegroundColor Green
    } else {
        Write-Warning "「$IssueTitle」というタイトルの課題が見つかりませんでした。"
    }
}

function Add-ErrorTrap {
    # 全コマンドのエラートラップを有効化するための関数
    
    # 元のErrorActionPreferenceを保存
    $script:OriginalErrorActionPreference = $ErrorActionPreference
    
    # エラーアクションをContinueに設定（エラーが発生してもスクリプトは続行）
    $ErrorActionPreference = "Continue"
    
    # エラートラップの設定
    trap {
        Write-Host "エラーが発生しました！" -ForegroundColor Red
        Write-Host "コマンド: $($_.InvocationInfo.Line)" -ForegroundColor Yellow
        Write-Host "エラー: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "Record-MDCError コマンドでこのエラーを記録できます:" -ForegroundColor Cyan
        Write-Host "Record-MDCError -FailedCommand '$($_.InvocationInfo.Line -replace "'", "''")' -Description 'エラーの説明'" -ForegroundColor Cyan
        
        # エラー後も処理を継続
        continue
    }
    
    Write-Host "MDCファーストエラートラップが有効になりました。エラー発生時に記録手順が表示されます。" -ForegroundColor Green
}

function Remove-ErrorTrap {
    # エラートラップを無効化するための関数
    
    # 元のErrorActionPreferenceに戻す
    if ($script:OriginalErrorActionPreference) {
        $ErrorActionPreference = $script:OriginalErrorActionPreference
    } else {
        $ErrorActionPreference = "Stop" # デフォルト
    }
    
    # トラップをリセット（PowerShellではトラップの直接的な無効化方法はないため、このアプローチは不完全）
    
    Write-Host "MDCファーストエラートラップが無効になりました。" -ForegroundColor Yellow
}
#endregion

#region エイリアス設定
# エイリアスの設定（短縮形）
Set-Alias -Name mdc-task -Value Start-MDCTask
Set-Alias -Name mdc-error -Value Record-MDCError
Set-Alias -Name mdc-ref -Value Open-MDCReference
Set-Alias -Name mdc-update -Value Update-MDCRecord
Set-Alias -Name mdc-trap -Value Add-ErrorTrap
Set-Alias -Name mdc-untrap -Value Remove-ErrorTrap

# カスタムプロンプト：現在のMDC作業状態を表示
function prompt {
    # 現在のプロジェクトルートディレクトリを取得
    $projectRoot = if (Test-Path ".git") {
        (Get-Location).Path
    } elseif (Test-Path "../.git") {
        (Get-Item "..").FullName
    } else {
        $null
    }
    
    if ($projectRoot) {
        # issues.mdから現在進行中の課題を取得（最大1件）
        $activeTasks = ""
        if (Test-Path "$projectRoot/issues.md") {
            $issuesContent = Get-Content -Path "$projectRoot/issues.md" -Raw
            $activePattern = "(?ms)\*\*\[[^\]]+\][^*]*?- ステータス: (進行中|作業開始)[^*]*?"
            $activeMatches = [regex]::Matches($issuesContent, $activePattern)
            
            if ($activeMatches.Count -gt 0) {
                $activeTask = $activeMatches[0].Value
                if ($activeTask -match "\*\*\[([^\]]+)\]([^*]*?)\*\*") {
                    $taskType = $Matches[1]
                    $taskTitle = $Matches[2].Trim()
                    $activeTasks = "[MDC:$taskType] "
                }
            }
        }
        
        # 通常のプロンプトと組み合わせる
        $currentPath = (Get-Location).Path.Replace($HOME, "~")
        Write-Host "$activeTasks" -NoNewline -ForegroundColor Magenta
        return "PS $currentPath> "
    } else {
        # プロジェクトルート外の場合は通常のプロンプト
        return "PS $($executionContext.SessionState.Path.CurrentLocation)> "
    }
}
#endregion

#region 自動ロード時の初期化
# スクリプトロード時のウェルカムメッセージ
Write-Host @"
========================================================
 MDCファーストアプローチ v1.0 - PowerShell統合
========================================================
 使用可能コマンド:
 - mdc-task <タイプ> [説明]  : MDC起点で作業開始
   タイプ: bug, feature, refactor, quality, mdc, test
 - mdc-error <コマンド> [説明]: エラーを記録
 - mdc-ref <参照タイプ>      : MDCドキュメント参照
 - mdc-update <課題> [状態]   : 課題状態を更新
 - mdc-trap                  : エラートラップ有効化
 - mdc-untrap                : エラートラップ無効化
========================================================
"@ -ForegroundColor Cyan

# 自動的にエラートラップを有効化（必要に応じてコメントアウト）
# Add-ErrorTrap
#endregion 