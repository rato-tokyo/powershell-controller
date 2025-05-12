"""
PowerShellプロセス管理モジュール

PowerShellプロセスの起動と終了を管理する機能を提供します。
"""

import asyncio
import subprocess
from typing import Optional, Tuple

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import PowerShellControllerSettings
from .errors import PowerShellShutdownError, PowerShellStartupError
from .utils.session_util import get_startup_info


class ProcessManager:
    """
    PowerShellプロセス管理クラス

    PowerShellプロセスの起動と終了を管理します。
    """

    def __init__(self, settings: PowerShellControllerSettings):
        """
        プロセス管理クラスを初期化します。

        Args:
            settings: セッションの設定
        """
        self.settings = settings
        self._process: Optional[asyncio.subprocess.Process] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        logger.debug("ProcessManagerが初期化されました")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True
    )
    async def start(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """
        PowerShellプロセスを開始します。

        Returns:
            Tuple[asyncio.StreamReader, asyncio.StreamWriter]: 標準出力と標準入力のストリーム

        Raises:
            PowerShellStartupError: PowerShellプロセスの起動に失敗した場合
        """
        if self._process:
            logger.debug("PowerShellプロセスは既に実行中です")
            return None, None

        try:
            # プロセスを起動
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    str(self.settings.powershell_path),
                    *self.settings.powershell_args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    startupinfo=get_startup_info(),
                    creationflags=subprocess.CREATE_NO_WINDOW if self.settings.hide_window else 0,
                ),
                timeout=10.0,
            )

            if not process.stdout or not process.stdin:
                raise PowerShellStartupError("PowerShellプロセスの起動に失敗しました")

            # ストリームを作成
            loop = asyncio.get_running_loop()
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            transport = await asyncio.wait_for(
                loop.connect_read_pipe(lambda: protocol, process.stdout), timeout=5.0
            )
            writer = asyncio.StreamWriter(process.stdin, protocol, reader, loop)

            self._process = process
            self._reader = reader
            self._writer = writer

            logger.info("PowerShellプロセスが開始されました")

            return reader, writer

        except asyncio.TimeoutError as e:
            logger.error("PowerShellプロセスの起動がタイムアウトしました")
            raise PowerShellStartupError("PowerShellプロセスの起動がタイムアウトしました") from e
        except Exception as e:
            logger.error(f"PowerShellプロセスの起動に失敗: {e}")
            raise PowerShellStartupError(f"PowerShellプロセスの起動に失敗しました: {e}") from e

    async def stop(self) -> None:
        """
        PowerShellプロセスを停止します。

        Raises:
            PowerShellShutdownError: PowerShellプロセスの終了に失敗した場合
        """
        if not self._process:
            logger.debug("PowerShellプロセスは実行されていません")
            return

        try:
            # プロセスを終了
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()

            # ストリームを閉じる
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()

            self._process = None
            self._reader = None
            self._writer = None

            logger.info("PowerShellプロセスが停止しました")

        except Exception as e:
            logger.error(f"PowerShellプロセスの停止に失敗: {e}")
            raise PowerShellShutdownError(f"PowerShellプロセスの停止に失敗しました: {e}") from e

    @property
    def is_running(self) -> bool:
        """
        プロセスが実行中かどうかを返します。

        Returns:
            bool: プロセスが実行中かどうか
        """
        if not self._process:
            return False
        return self._process.returncode is None
