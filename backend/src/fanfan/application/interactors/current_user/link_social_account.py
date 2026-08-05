import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import (
    LinkInitiatorMismatch,
    SocialAccountLinkedToAnotherUser,
    UserAlreadyHasProviderLinked,
)
from fanfan.core.models.social_identity import SocialIdentity
from fanfan.core.vo.social_identity import SocialProvider, generate_social_identity_id
from fanfan.core.vo.user import UserId

logger = logging.getLogger(__name__)


class LinkSocialAccountInput(BaseModel):
    provider: SocialProvider
    # The OIDC `sub` — the identity key, not the native account id.
    subject: str
    provider_user_id: int
    # Who started the flow, carried through the OAuth state. Guards against the
    # browser signing in as somebody else between the redirect and the callback.
    initiator_user_id: UserId


class LinkSocialAccount:
    """Attach a social identity to the current user, for any provider."""

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

    async def __call__(self, data: LinkSocialAccountInput) -> None:
        current_user = await self.current_user_provider.require_user()

        if current_user.id != data.initiator_user_id:
            logger.warning(
                "Social link refused: session changed mid-flow",
                extra={
                    "provider": data.provider.value,
                    "actor_id": str(current_user.id),
                    "initiator_id": str(data.initiator_user_id),
                },
            )
            raise LinkInitiatorMismatch

        current = await self.social_identity_gateway.get_by_provider(
            current_user.id, data.provider
        )
        if current is not None:
            if current.subject == data.subject:
                return
            raise UserAlreadyHasProviderLinked

        existing = await self.social_identity_gateway.get_by_subject(
            provider=data.provider, subject=data.subject
        )
        if existing is not None and existing.user_id != current_user.id:
            raise SocialAccountLinkedToAnotherUser

        await self.social_identity_gateway.add(
            SocialIdentity(
                id=generate_social_identity_id(),
                user_id=current_user.id,
                provider=data.provider,
                subject=data.subject,
                provider_user_id=data.provider_user_id,
            )
        )
        await self.uow.commit()
        logger.info(
            "Social account linked",
            extra={"provider": data.provider.value, "actor_id": str(current_user.id)},
        )
