import logging

from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.social_ids import SocialIdentityRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.exceptions.users import (
    TelegramAlreadyLinkedToAnotherUser,
    UserAlreadyHasTelegramLinked,
)
from fanfan.core.models.social_account import SocialIdentity
from fanfan.presentation.tgbot.config import TelegramConfig

logger = logging.getLogger(__name__)


class LinkTelegramAccountInput(BaseModel):
    user_id: int


class LinkTelegramAccount:
    def __init__(
        self,
        bot_config: TelegramConfig,
        user_repo: UserRepository,
        social_id_repo: SocialIdentityRepository,
        trx: TransactionManager,
        id_provider: IdProvider,
    ) -> None:
        self.social_id_repo = social_id_repo
        self.bot_config = bot_config
        self.user_repo = user_repo
        self.trx = trx
        self.id_provider = id_provider

    async def __call__(self, data: LinkTelegramAccountInput) -> None:
        provider_id = str(data.user_id)
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )

        current_telegram = await self.social_id_repo.get_by_provider(
            current_user.id, "telegram"
        )
        if current_telegram is not None:
            if current_telegram.provider_id == provider_id:
                return
            raise UserAlreadyHasTelegramLinked

        linked_user = await self.user_repo.get_by_social_id(
            provider_name="telegram", provider_account_id=provider_id
        )
        if linked_user is not None and linked_user.id != current_user.id:
            raise TelegramAlreadyLinkedToAnotherUser

        await self.social_id_repo.add(
            SocialIdentity(
                user_id=current_user.id,
                provider="telegram",
                provider_id=provider_id,
            )
        )
        await self.trx.commit()
        logger.info(
            "Telegram %s was linked to user %s",
            provider_id,
            current_user.id,
            extra={"user_id": str(current_user.id), "provider_id": provider_id},
        )
