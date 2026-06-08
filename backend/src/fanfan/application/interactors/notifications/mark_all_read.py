from datetime import datetime

from pytz import timezone

from fanfan.adapters.config.models import EnvConfig
from fanfan.application.ports.repositories.notifications import NotificationRepository
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider


class MarkAllRead:
    def __init__(
        self,
        notifications_repo: NotificationRepository,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
        config: EnvConfig,
    ):
        self.notifications_repo = notifications_repo
        self.current_user_provider = current_user_provider
        self.uow = uow
        self.config = config

    async def __call__(self) -> None:
        current_user_id = await self.current_user_provider.require_user_id()
        timestamp = datetime.now(tz=timezone(self.config.timezone))
        await self.notifications_repo.mark_all_read_for_user(
            user_id=current_user_id,
            timestamp=timestamp,
        )
        await self.uow.commit()
