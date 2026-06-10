import logging

from fanfan.application.ports.gateways.social_ids import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import (
    TelegramCannotBeUnlinkedWithoutEmail,
)

logger = logging.getLogger(__name__)


class UnlinkTelegramAccount:
    def __init__(
        self,
        user_repo: UserGateway,
        social_id_repo: SocialIdentityGateway,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.social_id_repo = social_id_repo
        self.user_repo = user_repo
        self.uow = uow
        self.current_user_provider = current_user_provider

    async def __call__(self) -> None:
        current_user = await self.current_user_provider.require_user()

        if current_user.email is None:
            raise TelegramCannotBeUnlinkedWithoutEmail

        # Keep delete idempotent so the profile can recover from stale UI safely.
        telegram_id = await self.social_id_repo.get_by_provider(
            user_id=current_user.id,
            provider="telegram",
        )
        if telegram_id:
            await self.social_id_repo.delete(telegram_id)
            await self.uow.commit()
            logger.info(
                "Telegram account was unlinked from user %s",
                current_user.id,
                extra={"user_id": str(current_user.id)},
            )
