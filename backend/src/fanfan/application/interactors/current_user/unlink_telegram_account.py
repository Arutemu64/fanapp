import logging

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.social_ids import SocialIdentityRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.exceptions.users import (
    TelegramCannotBeUnlinkedWithoutEmail,
)

logger = logging.getLogger(__name__)


class UnlinkTelegramAccount:
    def __init__(
        self,
        user_repo: UserRepository,
        social_id_repo: SocialIdentityRepository,
        trx: TransactionManager,
        id_provider: IdProvider,
    ) -> None:
        self.social_id_repo = social_id_repo
        self.user_repo = user_repo
        self.trx = trx
        self.id_provider = id_provider

    async def __call__(self) -> None:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )

        if current_user.email is None:
            raise TelegramCannotBeUnlinkedWithoutEmail

        # Keep delete idempotent so the profile can recover from stale UI safely.
        telegram_id = await self.social_id_repo.get_by_provider(
            user_id=current_user.id,
            provider="telegram",
        )
        if telegram_id:
            await self.social_id_repo.delete(telegram_id)
            await self.trx.commit()
            logger.info(
                "Telegram account was unlinked from user %s",
                current_user.id,
                extra={"user_id": str(current_user.id)},
            )
