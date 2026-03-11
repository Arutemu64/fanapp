import logging

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import (
    TelegramCannotBeUnlinkedWithoutEmail,
    UserNotFound,
)

logger = logging.getLogger(__name__)


class UnlinkTelegramAccount:
    def __init__(
        self, user_gateway: UserGateway, uow: UnitOfWork, id_provider: IdProvider
    ) -> None:
        self.user_gateway = user_gateway
        self.uow = uow
        self.id_provider = id_provider

    async def __call__(self) -> None:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated

            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound

            if current_user.email is None:
                raise TelegramCannotBeUnlinkedWithoutEmail

            # Keep delete idempotent so the profile can recover from stale UI safely.
            was_deleted = await self.user_gateway.delete_user_social_id_by_provider(
                current_user_id,
                "telegram",
            )
            if was_deleted:
                await self.uow.commit()
                logger.info(
                    "Telegram account was unlinked from user %s",
                    current_user_id,
                    extra={"user_id": str(current_user_id)},
                )
