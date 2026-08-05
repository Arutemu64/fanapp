import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.social_identity import SocialIdentityGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.users import CannotRemoveLastSignInMethod
from fanfan.core.vo.social_identity import SocialProvider

logger = logging.getLogger(__name__)


class UnlinkSocialAccountInput(BaseModel):
    provider: SocialProvider


class UnlinkSocialAccount:
    """Detach a social identity from the current user, for any provider."""

    def __init__(
        self,
        social_identity_gateway: SocialIdentityGateway,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
    ) -> None:
        self.social_identity_gateway = social_identity_gateway
        self.uow = uow
        self.current_user_provider = current_user_provider

    async def __call__(self, data: UnlinkSocialAccountInput) -> None:
        current_user = await self.current_user_provider.require_user()

        # Keep delete idempotent so the profile can recover from stale UI safely.
        identity = await self.social_identity_gateway.get_by_provider(
            user_id=current_user.id,
            provider=data.provider,
        )
        if identity is None:
            return

        # A user must keep at least one way to sign in. Email drives both password
        # and email-code login; each linked provider is itself a way in. So the
        # unlink is refused only when there is no email and this is the last
        # remaining identity — which would otherwise lock the user out.
        if current_user.email is None:
            linked_count = await self.social_identity_gateway.count_by_user(
                current_user.id
            )
            if linked_count <= 1:
                raise CannotRemoveLastSignInMethod

        await self.social_identity_gateway.delete(identity)
        await self.uow.commit()
        logger.info(
            "Social account unlinked",
            extra={"provider": data.provider.value, "actor_id": str(current_user.id)},
        )
