from datetime import datetime

from pytz import timezone

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.db.gateways.notifications import NotificationGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated


class MarkAllRead:
    def __init__(
        self,
        notifications_gateway: NotificationGateway,
        id_provider: IdProvider,
        uow: UnitOfWork,
        config: EnvConfig,
    ):
        self.notifications_gateway = notifications_gateway
        self.id_provider = id_provider
        self.uow = uow
        self.config = config

    async def __call__(self) -> None:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            timestamp = datetime.now(tz=timezone(self.config.timezone))
            await self.notifications_gateway.mark_all_read_for_user(
                user_id=current_user_id,
                timestamp=timestamp,
            )
            await self.uow.commit()
