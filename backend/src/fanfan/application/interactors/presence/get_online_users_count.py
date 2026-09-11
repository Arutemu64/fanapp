from pydantic import BaseModel

from fanfan.application.ports.presence import PresenceGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission


class OnlineUsersCountOutput(BaseModel):
    count: int


class GetOnlineUsersCount:
    """How many users are connected right now, for the organiser dashboard."""

    def __init__(
        self,
        presence_gateway: PresenceGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ):
        self.presence_gateway = presence_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self) -> OnlineUsersCountOutput:
        current_user = await self.current_user_provider.require_user()
        # Reuses users:read: the online figure is a fact about the user base, so
        # the grant that opens the user directory governs it too — no separate
        # permission (and its CHECK-constraint migration) for one stat.
        await self.perm_service.ensure(
            user=current_user, permission=Permission.USERS_READ
        )

        count = await self.presence_gateway.count_online()
        return OnlineUsersCountOutput(count=count)
