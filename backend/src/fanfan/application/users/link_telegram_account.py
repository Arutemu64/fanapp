import logging

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.auth.login_telegram import check_telegram_authorization
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import (
    TelegramAlreadyConnected,
    TelegramAlreadyLinked,
    UserNotFound,
)
from fanfan.core.models.social_account import SocialAccount
from fanfan.presentation.tgbot.config import BotConfig

logger = logging.getLogger(__name__)


class LinkTelegramAccountCommand(BaseModel):
    id: int
    first_name: str
    auth_date: int
    hash: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None


class LinkTelegramAccount:
    def __init__(
        self,
        bot_config: BotConfig,
        user_gateway: UserGateway,
        uow: UnitOfWork,
        id_provider: IdProvider,
    ) -> None:
        self.bot_config = bot_config
        self.user_gateway = user_gateway
        self.uow = uow
        self.id_provider = id_provider

    async def __call__(self, data: LinkTelegramAccountCommand) -> None:
        # Verify the widget payload before we touch the database.
        check_telegram_authorization(
            auth_data=data.model_dump(exclude_unset=True),
            bot_token=self.bot_config.token.get_secret_value(),
        )

        provider_id = str(data.id)

        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated

            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound

            current_telegram = await self.user_gateway.get_user_social_id_by_provider(
                current_user_id,
                "telegram",
            )
            if current_telegram is not None:
                if current_telegram.provider_id == provider_id:
                    return
                raise TelegramAlreadyConnected

            linked_user = await self.user_gateway.get_user_by_social_id(
                provider_name="telegram",
                provider_account_id=provider_id,
            )
            if linked_user is not None and linked_user.id != current_user_id:
                raise TelegramAlreadyLinked

            try:
                await self.user_gateway.add_user_social_id(
                    SocialAccount(
                        user_id=current_user_id,
                        provider="telegram",
                        provider_id=provider_id,
                    )
                )
                await self.uow.commit()
            except IntegrityError as exc:
                await self.uow.rollback()
                raise TelegramAlreadyLinked from exc
            else:
                logger.info(
                    "Telegram %s was linked to user %s",
                    provider_id,
                    current_user_id,
                    extra={"user_id": str(current_user_id), "provider_id": provider_id},
                )
