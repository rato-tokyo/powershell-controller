"""
PowerShell 7をPythonから制御するモジュール
セッションを維持したままコマンドを実行することができます。
"""
import subprocess
import sys
import logging
import time

class PowerShellController:
    def __init__(self):
        """
        PowerShell 7のコントローラーを初期化します。
        ログ設定も行います。
        """
        self.logger = self._setup_logger()
        self.powershell_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
        self.process = None
        self._start_powershell()

    def _setup_logger(self):
        """ロギングの設定を行います"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _start_powershell(self):
        """PowerShellプロセスを開始します"""
        try:
            self.process = subprocess.Popen(
                [self.powershell_path, "-NoProfile", "-NoLogo"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.logger.info("PowerShellセッションを開始しました")
            # プロンプトの変更
            self.execute_command('$host.ui.RawUI.WindowTitle = "Python Controlled PS"')
        except Exception as e:
            self.logger.error(f"PowerShellの起動に失敗しました: {e}")
            raise

    def execute_command(self, command):
        """
        コマンドを実行し、結果を返します
        
        Args:
            command (str): 実行するPowerShellコマンド
            
        Returns:
            str: コマンドの実行結果
        """
        try:
            self.logger.info(f"コマンドを実行: {command}")
            
            # 特殊なマーカーを使用して出力の終わりを判断
            marker = f"CMD_END_{time.time()}"
            
            # コマンドとマーカーを書き込み
            self.process.stdin.write(f"{command}; echo '{marker}'\n")
            self.process.stdin.flush()
            
            # 結果を読み取り
            output = []
            while True:
                line = self.process.stdout.readline().rstrip()
                if line == marker:
                    break
                if line:
                    output.append(line)
            
            # 現在のディレクトリを取得
            self.process.stdin.write("$PWD.Path; echo 'PWD_END'\n")
            self.process.stdin.flush()
            
            while True:
                line = self.process.stdout.readline().rstrip()
                if line == 'PWD_END':
                    break
                if line:
                    self.logger.info(f"現在のディレクトリ: {line}")
                    break
            
            return "\n".join(output)
            
        except Exception as e:
            self.logger.error(f"コマンド実行中にエラーが発生しました: {e}")
            raise

    def close(self):
        """PowerShellセッションを終了します"""
        if self.process:
            try:
                self.process.stdin.write("exit\n")
                self.process.stdin.flush()
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                pass
            finally:
                self.logger.info("PowerShellセッションを終了しました")

def main():
    """メイン処理"""
    controller = PowerShellController()
    try:
        # 初期ディレクトリを表示
        print("現在のディレクトリ:")
        result = controller.execute_command("pwd")
        print(result)
        
        # cd .. を2回実行
        print("\n1回目のcd..")
        result = controller.execute_command("cd ..")
        
        print("\n2回目のcd..")
        result = controller.execute_command("cd ..")
        
        # 最終的な位置を確認
        print("\n最終的な位置:")
        result = controller.execute_command("pwd")
        print(result)
        
    finally:
        controller.close()

if __name__ == "__main__":
    main() 