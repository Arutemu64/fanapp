import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import (
    LinkInitiatorMismatch,
    TelegramAlreadyLinkedToAnotherUser,
    UserAlreadyHasTelegramLinked,
)
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.vo.social_identity import SocialProvider, generate_social_identity_id
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)


class LinkTelegramAccountInput(BaseModel):
    # The OIDC `sub` — the identity key, not the Bot API user id.
    subject: str
    provider_user_id: int | None
    # Who started the flow, carried through the OAuth state. Guards against the
    # browser signing in as somebody else between the redirect and the callback.
    initiator_user_id: UserId


class LinkTelegramAccount:
    def __init__(
        self,
        user_gateway: UserGateway,
        social_identity_gateway: SocialIdentityGateway,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.social_identity_gateway = social_identity_gateway
        self.user_gateway = user_gateway
        self.uow = uow
        self.current_user_provider = current_user_provider

    async def __call__(self, data: LinkTelegramAccountInput) -> None:
        current_user = await self.current_user_provider.require_user()

        if current_user.id != data.initiator_user_id:
            logger.warning(
                "Telegram link refused: session changed mid-flow",
                extra={
                    "actor_id": str(current_user.id),
                    "initiator_id": str(data.initiator_user_id),
                },
            )
            raise LinkInitiatorMismatch

        current_telegram = await self.social_identity_gateway.get_by_provider(
            current_user.id, SocialProvider.TELEGRAM
        )
        if current_telegram is not None:
            if current_telegram.subject == data.subject:
                return
            raise UserAlreadyHasTelegramLinked

        existing = await self.social_identity_gateway.get_by_subject(
            provider=SocialProvider.TELEGRAM, subject=data.subject
        )
        if existing is not None and existing.user_id != current_user.id:
            raise TelegramAlreadyLinkedToAnotherUser

        await self.social_identity_gateway.add(
            SocialIdentity(
                id=generate_social_identity_id(),
                user_id=current_user.id,
                provider=SocialProvider.TELEGRAM,
                subject=data.subject,
                provider_user_id=data.provider_user_id,
            )
        )
        await self.uow.commit()
        logger.info(
            "Telegram account linked",
            extra={"actor_id": str(current_user.id)},
        )
