# AI実装機能
# 実行計画に基づいて実装を行うスクリプト
#
# 使用方法:
#   & ./ai_implementer.ps1 -PlanPath <計画ファイルパス> [-Mode <実行モード>]

param (
    [Parameter(Mandatory = $true)]
    [string]$PlanPath,
    
    [Parameter(Mandatory = $false)]
    [ValidateSet("interactive", "automatic", "review_only")]
    [string]$Mode = "interactive"
)

# 現在の作業ディレクトリを取得
$workingDir = Get-Location

Write-Host "AI実装を開始します: 計画=$PlanPath, モード=$Mode" -ForegroundColor Cyan

# 計画ファイルが存在するか確認
if (-not (Test-Path $PlanPath)) {
    Write-Error "計画ファイルが見つかりません: $PlanPath"
    return
}

# 計画の内容を読み込む
$planContent = Get-Content -Path $PlanPath -Raw
Write-Host "計画の内容を読み込みました。" -ForegroundColor Green

# 計画からステップを抽出
function Extract-ImplementationSteps {
    param (
        [string]$PlanContent
    )
    
    $steps = @()
    
    # 正規表現で「## 実行ステップ」セクションを抽出
    if ($PlanContent -match "## 実行ステップ([\s\S]*?)##") {
        $stepsSection = $Matches[1]
        
        # 各ステップを抽出（数字.で始まる行）
        $stepMatches = [regex]::Matches($stepsSection, "\d+\.\s+\*\*(.*?)\*\*([\s\S]*?)(?=\d+\.\s+\*\*|\Z)")
        
        foreach ($match in $stepMatches) {
            $stepTitle = $match.Groups[1].Value.Trim()
            $stepContent = $match.Groups[2].Value.Trim()
            
            # ファイルパスを抽出（```で囲まれた部分）
            $files = @()
            $fileMatches = [regex]::Matches($stepContent, "```\s*(.*?)\s*```")
            
            foreach ($fileMatch in $fileMatches) {
                $files += $fileMatch.Groups[1].Value.Trim()
            }
            
            $steps += [PSCustomObject]@{
                Title = $stepTitle
                Description = $stepContent -replace "```.*?```", ""
                Files = $files
            }
        }
    }
    
    return $steps
}

# カスタマイズポイント: AIモデルへの接続方法を実装
function Invoke-AIModelAPI {
    param (
        [string]$Prompt,
        [string]$Model = "gpt-4",
        [int]$MaxTokens = 2000
    )
    
    # ここに実際のAI API呼び出しコードを追加
    # 例: OpenAI GPT API、Claude API、Azure OpenAI API など
    
    # テスト用のダミー実装（実際の実装に置き換えてください）
    Write-Host "AI APIを呼び出し中..." -ForegroundColor Magenta
    
    # ===== カスタマイズ開始 =====
    # 以下のコードを実際のAPI呼び出しに置き換えてください
    
    # ダミーのコード生成（実際のAI実装に置き換えてください）
    $filePath = $Prompt -replace ".*ファイル `"(.*?)`".*", '$1'
    $fileContent = ""
    
    # ファイル種類に応じてダミーコードを生成
    if ($filePath -match "\.py$") {
        # Pythonファイル
        if ($filePath -match "test_") {
            # テストファイル
            $fileContent = @"
import unittest
from unittest.mock import MagicMock, patch

class TestExample(unittest.TestCase):
    def setUp(self):
        # テスト準備
        self.test_obj = MagicMock()
        
    def test_basic_functionality(self):
        # 基本機能のテスト
        self.assertTrue(True)
        
    def test_edge_case(self):
        # エッジケースのテスト
        self.assertIsNone(None)
        
    def test_error_handling(self):
        # エラー処理のテスト
        with self.assertRaises(ValueError):
            raise ValueError("テストエラー")
            
if __name__ == '__main__':
    unittest.main()
"@
        } else {
            # 通常のPythonファイル
            $fileContent = @"
# 自動生成されたPythonファイル
# ファイルパス: $filePath

class ExampleClass:
    """サンプルクラス"""
    
    def __init__(self):
        """コンストラクタ"""
        self.value = None
        
    def set_value(self, value):
        """値を設定する
        
        Args:
            value: 設定する値
        """
        self.value = value
        
    def get_value(self):
        """値を取得する
        
        Returns:
            設定された値
        """
        return self.value
        
    def process(self):
        """処理を実行する"""
        if self.value is None:
            raise ValueError("値が設定されていません")
        return self.value * 2

def main():
    """メイン関数"""
    example = ExampleClass()
    example.set_value(10)
    result = example.process()
    print(f"処理結果: {result}")
    
if __name__ == "__main__":
    main()
"@
        }
    } elseif ($filePath -match "\.(md|markdown)$") {
        # Markdownファイル
        $fileContent = @"
# サンプルドキュメント

## 概要
このドキュメントは自動生成されたサンプルです。

## 使用方法
1. ステップ1を実行します
2. ステップ2を実行します
3. ステップ3を実行します

## コード例
```python
def example_function():
    return "Hello World"
```

## 注意事項
- 注意点1
- 注意点2
- 注意点3
"@
    } else {
        # その他のファイル
        $fileContent = @"
// 自動生成されたファイル
// ファイルパス: $filePath

// このファイルはAIによって生成されたサンプルです。
// 実際のプロジェクト要件に合わせて修正してください。
"@
    }
    
    # ===== カスタマイズ終了 =====
    
    return $fileContent
}

# ファイルを作成または更新する関数
function Create-OrUpdateFile {
    param (
        [string]$FilePath,
        [string]$Content
    )
    
    # ディレクトリが存在しない場合は作成
    $directory = Split-Path -Path $FilePath -Parent
    if (-not [string]::IsNullOrEmpty($directory) -and -not (Test-Path $directory)) {
        New-Item -Path $directory -ItemType Directory -Force | Out-Null
        Write-Host "ディレクトリを作成しました: $directory" -ForegroundColor Yellow
    }
    
    # ファイルを作成または更新
    Set-Content -Path $FilePath -Value $Content -Encoding UTF8
    Write-Host "ファイルを作成/更新しました: $FilePath" -ForegroundColor Green
}

# 実行ステップを抽出
$steps = Extract-ImplementationSteps -PlanContent $planContent

if ($steps.Count -eq 0) {
    Write-Warning "計画から実行ステップを抽出できませんでした。"
    return
}

Write-Host "`n計画から ${$steps.Count} 個の実行ステップを抽出しました。" -ForegroundColor Cyan

# レビューのみモードの場合は計画の内容を表示して終了
if ($Mode -eq "review_only") {
    Write-Host "`n===== 実行計画の内容 =====" -ForegroundColor Yellow
    Get-Content $PlanPath | ForEach-Object { Write-Host $_ }
    Write-Host "===== 実行計画終了 =====" -ForegroundColor Yellow
    
    Write-Host "`n実行ステップ一覧:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $steps.Count; $i++) {
        Write-Host "$($i+1). $($steps[$i].Title)" -ForegroundColor Yellow
        Write-Host "   対象ファイル: $($steps[$i].Files -join ', ')" -ForegroundColor Gray
    }
    
    Write-Host "`nレビューのみモードのため、実行はスキップします。" -ForegroundColor Magenta
    return
}

# 各ステップを実行
for ($i = 0; $i -lt $steps.Count; $i++) {
    $step = $steps[$i]
    
    Write-Host "`n【ステップ $($i+1)/$($steps.Count)】$($step.Title)" -ForegroundColor Yellow
    Write-Host $step.Description -ForegroundColor Gray
    
    # インタラクティブモードの場合はユーザー確認
    if ($Mode -eq "interactive") {
        $confirmation = Read-Host "このステップを実行しますか？ (Y/N/S - Yesは実行、Nはスキップ、Sは残りをスキップ)"
        
        if ($confirmation -eq "S" -or $confirmation -eq "s") {
            Write-Host "ユーザーの指示により残りのステップをスキップします。" -ForegroundColor Yellow
            break
        }
        
        if ($confirmation -ne "Y" -and $confirmation -ne "y") {
            Write-Host "ステップをスキップします。" -ForegroundColor Yellow
            continue
        }
    }
    
    # ファイルの生成と更新
    foreach ($file in $step.Files) {
        # ファイルパスの検証と正規化
        $filePath = $file.Trim()
        
        # 相対パスを絶対パスに変換
        if (-not [System.IO.Path]::IsPathRooted($filePath)) {
            $filePath = Join-Path $workingDir $filePath
        }
        
        Write-Host "ファイル `"$filePath`" の生成/更新を開始します..." -ForegroundColor Cyan
        
        # AIにファイルの内容を生成させる
        $prompt = @"
以下の実行ステップに基づいて、ファイル `"$filePath`" の内容を生成してください。

ステップ: $($step.Title)
説明: $($step.Description)

生成する内容は、実際のコードやドキュメントとして有効な形式にしてください。
コメントや説明は適切に入れてください。
"@
        
        $fileContent = Invoke-AIModelAPI -Prompt $prompt
        
        # インタラクティブモードの場合はファイル内容を表示して確認
        if ($Mode -eq "interactive") {
            Write-Host "`n===== 生成されたファイル内容 =====" -ForegroundColor Yellow
            Write-Host $fileContent
            Write-Host "===== ファイル内容終了 =====" -ForegroundColor Yellow
            
            $fileConfirmation = Read-Host "このファイルを作成/更新しますか？ (Y/N)"
            
            if ($fileConfirmation -ne "Y" -and $fileConfirmation -ne "y") {
                Write-Host "ファイルの作成/更新をスキップします。" -ForegroundColor Yellow
                continue
            }
        }
        
        # ファイルを作成または更新
        Create-OrUpdateFile -FilePath $filePath -Content $fileContent
    }
    
    Write-Host "ステップ $($i+1) の実行が完了しました。" -ForegroundColor Green
}

Write-Host "`nAI実装が完了しました。" -ForegroundColor Green
if ($Mode -eq "interactive" -or $Mode -eq "automatic") {
    Write-Host "生成されたファイルを確認し、必要に応じて修正してください。" -ForegroundColor Cyan
} 