# MDCファーストアプローチ - AI主導モード専用スクリプト
# AI主導モードのみをサポートするシンプル版

# 設定
$MDC_DIR = Join-Path $PSScriptRoot "../../.cursor/rules"
$TASKS_DIR = Join-Path $PSScriptRoot "../tasks"
$ISSUES_FILE = Join-Path $PSScriptRoot "../../../issues.md"

# ディレクトリ確認
if (-not (Test-Path $TASKS_DIR)) {
    New-Item -Path $TASKS_DIR -ItemType Directory -Force | Out-Null
}

# タスク開始（AI主導）
function Start-AITask {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Description
    )
    
    # タスクIDを生成
    $date = Get-Date -Format "yyyyMMdd_HHmmss"
    $taskId = "ai_task_$date"
    $taskFile = Join-Path $TASKS_DIR "$taskId.mdc"
    
    # MDCファイルを生成
    $taskMDC = @"
# AI主導タスク: $Description

## 概要
このタスクはAI主導モードで実行されます。AIは問題分析から実装、テスト、ドキュメント作成まで主導し、ユーザーはレビューと承認を担当します。

## タスク詳細
- 課題: $Description
- 開始日: $(Get-Date -Format "yyyy-MM-dd")
- 担当: AI (レビュー: ユーザー)
- 状態: 未着手

## 指示
以下の課題を自動的に分析して実装してください:

$Description

## 期待される成果物
- 問題の分析
- 実装計画
- コード実装
- テスト
- ドキュメント更新

## 承認プロセス
1. 実装計画を提案し、ユーザーの承認を得る
2. 承認後、実装を行う
3. 実装完了後、レビューを受ける
4. 問題があれば修正、なければ完了

## 備考
このMDCは自動生成されています。必要に応じて編集してください。
"@
    
    # MDCファイルを保存
    Set-Content -Path $taskFile -Value $taskMDC
    
    # issues.mdに追記
    $issueEntry = @"

**[AI主導] $Description**
- 開始日: $(Get-Date -Format "yyyy-MM-dd")
- 状態: 未着手
- MDCファイル: $taskFile
- 更新日: $(Get-Date -Format "yyyy-MM-dd")
"@
    
    Add-Content -Path $ISSUES_FILE -Value $issueEntry
    
    # タスクファイルを開く
    Write-Host "AI主導タスクを開始しました: $Description" -ForegroundColor Green
    Write-Host "MDCファイル: $taskFile" -ForegroundColor Cyan
    Write-Host "Cursorチャットで以下のように入力してタスクを進めてください:" -ForegroundColor Yellow
    Write-Host ".cursor/rules/flows/main.mdcと$taskFileに基づいて、「$Description」を実装してください。" -ForegroundColor White
    
    # オプションでファイルを開く
    if ($env:EDITOR) {
        & $env:EDITOR $taskFile
    }
    else {
        notepad $taskFile
    }
    
    return $taskFile
}

# タスク生成（より詳細な指示が必要な場合）
function New-AITaskMDC {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Description
    )
    
    # Start-AITaskと同様の処理だが、より詳細な課題定義のテンプレートを提供
    $date = Get-Date -Format "yyyyMMdd_HHmmss"
    $taskId = "ai_detailed_$date"
    $taskFile = Join-Path $TASKS_DIR "$taskId.mdc"
    
    # より詳細なMDCテンプレート
    $taskMDC = @"
# 詳細AI主導タスク: $Description

## 背景と課題
以下の課題について詳細に説明します:

$Description

<!-- ここに課題の背景や詳細情報を追加してください -->

## 具体的な要件
<!-- 具体的な要件を箇条書きで記述してください -->
- 要件1
- 要件2
- 要件3

## 制約条件
<!-- 実装時の制約条件があれば記述してください -->
- 制約1
- 制約2

## 参考情報
<!-- 参考になる情報、関連ファイル、URIなどを記述してください -->
- 参考1
- 参考2

## 期待される成果物
- 問題の分析
- 実装計画
- コード実装
- テスト
- ドキュメント更新

## 承認プロセス
1. 実装計画を提案し、ユーザーの承認を得る
2. 承認後、実装を行う
3. 実装完了後、レビューを受ける
4. 問題があれば修正、なければ完了

## 備考
このMDCは自動生成されています。実装を依頼する前に必要な情報を追加してください。
"@
    
    # MDCファイルを保存
    Set-Content -Path $taskFile -Value $taskMDC
    
    # issues.mdには追記しない（編集完了後に手動で追記するため）
    
    # タスクファイルを開く
    Write-Host "詳細AI主導タスクテンプレートを生成しました" -ForegroundColor Green
    Write-Host "MDCファイル: $taskFile" -ForegroundColor Cyan
    Write-Host "テンプレートを編集し、必要な情報を追加してください" -ForegroundColor Yellow
    
    # オプションでファイルを開く
    if ($env:EDITOR) {
        & $env:EDITOR $taskFile
    }
    else {
        notepad $taskFile
    }
    
    return $taskFile
}

# エラー記録
function Record-Error {
    param (
        [Parameter(Mandatory = $true)]
        [string]$Command,
        
        [Parameter(Mandatory = $true)]
        [string]$Description
    )
    
    # issues.mdにエラーを記録
    $errorEntry = @"

**[PowerShell] エラー発生**
- 問題: PowerShellコマンド実行中にエラーが発生
- 発生環境: Windows $(([System.Environment]::OSVersion.Version).ToString()), PowerShell $($PSVersionTable.PSVersion)
- 失敗コマンド: `$Command`
- 説明: $Description
- ステータス: 未解決
- 更新日: $(Get-Date -Format "yyyy-MM-dd")
"@
    
    Add-Content -Path $ISSUES_FILE -Value $errorEntry
    
    Write-Host "エラーを記録しました" -ForegroundColor Yellow
    Write-Host "エラー詳細: $Description" -ForegroundColor Red
    Write-Host "コマンド: $Command" -ForegroundColor Gray
    Write-Host "issues.md に記録されました" -ForegroundColor Cyan
    
    # AIに解決を依頼するためのヒント
    Write-Host "`nAIに解決を依頼するには、Cursorチャットで以下のように入力してください:" -ForegroundColor Green
    Write-Host "「このエラーの解決策を提案してください: $Description」" -ForegroundColor White
}

# エラートラップ有効化
function Enable-ErrorTrap {
    # エラーアクションの設定
    $global:ErrorActionPreference = "Continue"
    
    # エラートラップ関数
    $global:ErrorTrapAction = {
        param($Command, $ErrorRecord)
        
        # ユーザーに記録するかどうか確認
        Write-Host "`nエラーが発生しました:" -ForegroundColor Red
        Write-Host $ErrorRecord -ForegroundColor Red
        
        $confirmation = Read-Host "このエラーを記録しますか？ (Y/N)"
        
        if ($confirmation -eq 'Y' -or $confirmation -eq 'y') {
            Record-Error -Command $Command -Description $ErrorRecord.Exception.Message
        }
    }
    
    # コマンド実行のフック
    $ExecutionContext.InvokeCommand.PreCommandLookupAction = {
        param($CommandName, $CommandLookupEventArgs)
        
        # 現在のコマンドを記録
        $global:LastCommand = $CommandName
    }
    
    # エラーイベントのハンドラ登録
    $null = Register-ObjectEvent -InputObject $ExecutionContext.InvokeCommand -EventName CommandNotFound -Action {
        & $global:ErrorTrapAction $global:LastCommand $Event.SourceEventArgs
    }
    
    $null = Register-EngineEvent -SourceIdentifier PowerShell.OnIdle -Action {
        if ($global:Error.Count -gt 0 -and $global:LastErrorCount -lt $global:Error.Count) {
            $latestError = $global:Error[0]
            & $global:ErrorTrapAction $global:LastCommand $latestError
            $global:LastErrorCount = $global:Error.Count
        }
    }
    
    # 初期エラーカウント設定
    $global:LastErrorCount = $global:Error.Count
    
    Write-Host "エラートラップが有効化されました" -ForegroundColor Green
    Write-Host "コマンド実行時にエラーが発生した場合、自動的に記録オプションが表示されます" -ForegroundColor Cyan
}

# タスク進捗更新
function Update-TaskStatus {
    param (
        [Parameter(Mandatory = $true)]
        [string]$TaskDescription,
        
        [Parameter(Mandatory = $true)]
        [ValidateSet("進行中", "レビュー待ち", "完了", "中断")]
        [string]$Status,
        
        [string]$Comment = ""
    )
    
    $issuesContent = Get-Content -Path $ISSUES_FILE -Raw
    
    # 該当するタスクを検索して更新
    $pattern = "(?s)\*\*\[AI主導\] $([regex]::Escape($TaskDescription))\*\*.*?- 状態: .*?(\r?\n)"
    $replacement = "**[AI主導] $TaskDescription**$&- 状態: $Status$1"
    
    if ($Comment) {
        $replacement = "**[AI主導] $TaskDescription**$&- 状態: $Status (備考: $Comment)$1"
    }
    
    $newContent = $issuesContent -replace $pattern, $replacement
    
    # コメントを追加
    $updateNote = "- 更新日: $(Get-Date -Format "yyyy-MM-dd")"
    $newContent = $newContent -replace "(?s)(\*\*\[AI主導\] $([regex]::Escape($TaskDescription))\*\*.*?)- 更新日: .*?(\r?\n)", "`$1$updateNote`$3"
    
    # ファイルに書き戻す
    Set-Content -Path $ISSUES_FILE -Value $newContent
    
    Write-Host "タスク「$TaskDescription」の状態を「$Status」に更新しました" -ForegroundColor Green
}

# エクスポート
Export-ModuleMember -Function Start-AITask, New-AITaskMDC, Record-Error, Enable-ErrorTrap, Update-TaskStatus

# エイリアス設定
Set-Alias -Name mdc-ai-task -Value Start-AITask
Set-Alias -Name mdc-ai-gen -Value New-AITaskMDC
Set-Alias -Name mdc-error -Value Record-Error
Set-Alias -Name mdc-trap -Value Enable-ErrorTrap
Set-Alias -Name mdc-update -Value Update-TaskStatus

# 初回読み込み時のメッセージ
Write-Host @"
====================================================
    MDCファーストアプローチ - AI主導モード
====================================================

利用可能なコマンド:
- mdc-ai-task "<課題の説明>"   : AI主導タスクを開始
- mdc-ai-gen "<課題の説明>"    : 詳細なAI主導タスクテンプレートを生成
- mdc-error "<コマンド>" "<説明>" : エラーを記録
- mdc-trap                     : エラートラップを有効化
- mdc-update "<タスク>" "<状態>" : タスク状態を更新

詳細なガイドは .cursor/rules/AI_MODE_GUIDE.md を参照してください
"@ -ForegroundColor Cyan 