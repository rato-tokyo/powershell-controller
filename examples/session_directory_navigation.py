"""
セッションを維持したままディレクトリ移動を行うサンプル
"""
import logging
import os
import sys

# パスの追加（開発環境での実行用）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.powershell_controller.simple import SimplePowerShellController

def setup_logger():
    """ロガーの設定"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # コンソールハンドラーの設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

def main():
    """メイン処理"""
    logger = setup_logger()
    logger.info("PowerShell 7を使用してセッションを維持したままディレクトリ移動を行います")

    # コントローラーの初期化
    controller = SimplePowerShellController()

    try:
        # セッションを維持したままコマンドを順次実行
        commands = [
            # 現在のディレクトリを表示
            "$PWD.Path",

            # ディレクトリ移動（1回目）
            "cd ..",
            "$PWD.Path",

            # ディレクトリ移動（2回目）
            "cd ..",
            "$PWD.Path",

            # ディレクトリの内容を表示
            "Get-ChildItem -Name"
        ]

        logger.info("コマンドの一括実行を開始")
        results = controller.execute_commands_in_session(commands)

        # 結果の表示
        logger.info("----- 実行結果 -----")
        for i, result in enumerate(results):
            if i == 0:
                logger.info(f"初期ディレクトリ: {result}")
            elif i == 2:
                logger.info(f"1階層上のディレクトリ: {result}")
            elif i == 4:
                logger.info(f"2階層上のディレクトリ: {result}")
            elif i == 6:
                logger.info(f"ディレクトリの内容:\n{result}")

        # 別の方法: スクリプトファイルを使用
        logger.info("\n----- 方法2: PowerShellスクリプト使用 -----")
        ps_script = """
        # 初期ディレクトリを記録
        $initialDir = $PWD.Path
        Write-Output "初期ディレクトリ: $initialDir"

        # 1つ上のディレクトリに移動
        cd ..
        $dir1 = $PWD.Path
        Write-Output "1階層上のディレクトリ: $dir1"

        # さらに1つ上のディレクトリに移動
        cd ..
        $dir2 = $PWD.Path
        Write-Output "2階層上のディレクトリ: $dir2"

        # 現在のディレクトリの内容を表示
        Write-Output "ディレクトリの内容:"
        Get-ChildItem -Name
        """

        logger.info("PowerShellスクリプトを実行")
        script_result = controller.execute_script(ps_script)
        logger.info(f"スクリプト実行結果:\n{script_result}")

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
    finally:
        logger.info("処理を終了します")

if __name__ == "__main__":
    main() 