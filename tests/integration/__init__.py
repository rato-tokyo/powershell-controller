"""
PowerShellコントローラーのテストパッケージ
"""

import os

# テスト用のモック設定
os.environ["POWERSHELL_TEST_MOCK"] = "true"
