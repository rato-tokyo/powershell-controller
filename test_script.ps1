$Text = "これは日本語のテストです"
$EncodedText = [System.Text.Encoding]::UTF8.GetBytes($Text)
$DecodedText = [System.Text.Encoding]::UTF8.GetString($EncodedText)
Write-Host "元のテキスト: $Text"
Write-Host "デコードされたテキスト: $DecodedText" 