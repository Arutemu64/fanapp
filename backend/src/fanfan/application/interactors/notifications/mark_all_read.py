from datetime import datetime

from pytz import timezone

from fanfan.adapters.config.models import EnvConfig
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.notifications import NotificationRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.exceptions.auth import UserNotAuthenticated


class MarkAllRead:
    def __init__(
        self,
        notifications_repo: NotificationRepository,
        id_provider: IdProvider,
        trx: TransactionManager,
        config: EnvConfig,
    ):
        self.notifications_repo = notifications_repo
        self.id_provider = id_provider
        self.trx = trx
        self.config = config

    async def __call__(self) -> None:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        timestamp = datetime.now(tz=timezone(self.config.timezone))
        await self.notifications_repo.mark_all_read_for_user(
            user_id=current_user_id,
            timestamp=timestamp,
        )
        await self.trx.commit()
