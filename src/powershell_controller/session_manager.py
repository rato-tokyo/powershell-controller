"""
PowerShellセッション管理を担当するモジュール

このモジュールはPowerShellセッションの作成・管理・再利用を行うクラスを提供します。
"""
from typing import Optional
import asyncio
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .core.session import PowerShellSession
from .core.errors import PowerShellError, ProcessError, PowerShellTimeoutError
from .utils.config import PowerShellControllerSettings

class SessionManager:
    """
    PowerShellセッションを管理するクラス
    
    このクラスはPowerShellセッションのライフサイクル（作成・取得・再利用・クリーンアップ）を管理します。
    """
    
    def __init__(self, settings: PowerShellControllerSettings):
        """
        セッションマネージャーを初期化します。
        
        Args:
            settings: PowerShellコントローラーの設定
        """
        self.settings = settings
        self._session: Optional[PowerShellSession] = None
        self._session_lock = asyncio.Lock()  # セッションアクセスの排他制御用
        self.logger = logger.bind(module="session_manager")
        
    async def get_session(self) -> PowerShellSession:
        """
        PowerShellセッションを取得します。
        セッションが存在しない場合は新しく作成します。
        
        Returns:
            PowerShellSession: 使用可能なPowerShellセッション
            
        Raises:
            PowerShellError: セッションの作成に失敗した場合
        """
        async with self._session_lock:
            if self._session is None:
                self.logger.debug("新しいセッションを作成")
                await self._create_session()
            return self._session
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=1, max=5),
        retry=retry_if_exception_type((ProcessError, PowerShellTimeoutError)),
        before_sleep=lambda retry_state: logger.info(
            f"セッション作成リトライ {retry_state.attempt_number}/3 - "
            f"前回エラー: {retry_state.outcome.exception()}"
        )
    )
    async def _create_session(self) -> None:
        """
        新しいPowerShellセッションを作成します。
        リトライロジック付き。
        
        Raises:
            PowerShellError: セッション作成に失敗した場合
        """
        try:
            self.logger.info("PowerShellセッションを作成しています")
            session = PowerShellSession(settings=self.settings)
            await session.__aenter__()
            self._session = session
            self.logger.info("PowerShellセッションの作成に成功しました")
        except Exception as e:
            self.logger.error(f"PowerShellセッションの作成に失敗: {e}")
            # 失敗した場合は明示的にNoneを設定
            self._session = None
            raise
    
    async def reset_session(self) -> None:
        """
        セッションをリセットします。
        エラーが発生した場合やセッションが不安定な状態になった場合に呼び出されます。
        
        存在するセッションをクリーンアップし、新しいセッションは次回get_sessionが呼ばれた際に作成されます。
        """
        async with self._session_lock:
            self.logger.warning("セッションをリセットしています")
            if self._session:
                try:
                    await self._session.cleanup()
                except Exception as e:
                    self.logger.error(f"セッションクリーンアップ中にエラーが発生: {e}")
                finally:
                    self._session = None
            self.logger.info("セッションのリセットが完了しました")
    
    async def close(self) -> None:
        """
        全てのセッションリソースを解放します。
        コントローラーの終了時またはプログラム終了時に呼び出されます。
        """
        async with self._session_lock:
            if self._session:
                try:
                    self.logger.debug("セッションをクリーンアップしています")
                    await self._session.__aexit__(None, None, None)
                except Exception as e:
                    self.logger.error(f"セッションのクリーンアップ中にエラーが発生: {e}")
                finally:
                    self._session = None
                    self.logger.info("セッションのクリーンアップが完了しました")
    
    async def restart_session(self) -> PowerShellSession:
        """
        セッションを再起動します。
        既存のセッションを終了し、新しいセッションを作成して返します。
        
        Returns:
            PowerShellSession: 新しく作成されたPowerShellセッション
        """
        async with self._session_lock:
            # 既存のセッションをクリーンアップ
            if self._session:
                try:
                    await self._session.__aexit__(None, None, None)
                except Exception as e:
                    self.logger.error(f"セッション再起動中のクリーンアップでエラーが発生: {e}")
                finally:
                    self._session = None
            
            # 新しいセッションを作成
            await self._create_session()
            return self._session 