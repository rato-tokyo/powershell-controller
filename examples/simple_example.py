#!/usr/bin/env python3
"""
PowerShell Controllerの簡単な使用例：
基本的なディレクトリ操作
"""
from powershell_controller.simple import SimplePowerShellController, PowerShellControllerConfig

def main():
    # ログ出力を抑制する設定
    config = PowerShellControllerConfig(
        log_level="ERROR"  # ERRORレベル以上のログのみ出力
    )
    controller = SimplePowerShellController(config=config)
    
    # 現在のディレクトリの内容を取得
    current_dir = controller.execute_command("Get-ChildItem | Format-Table -AutoSize | Out-String")
    print("現在のディレクトリ:")
    print(current_dir)

    # 1つ上のディレクトリに移動して内容を取得
    commands = [
        "Set-Location ..",
        "Get-ChildItem | Format-Table -AutoSize | Out-String"
    ]
    parent_dir = controller.execute_commands_in_session(commands)
    print("\n親ディレクトリ:")
    print(parent_dir[-1])

if __name__ == "__main__":
    main() 