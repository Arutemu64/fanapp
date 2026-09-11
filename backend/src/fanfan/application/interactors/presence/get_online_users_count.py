from pydantic import BaseModel

from fanfan.application.ports.presence import PresenceGateway
from fanfan.application.services.current_user import CurrentUserProvider


class OnlineUsersCountOutput(BaseModel):
    count: int


class GetOnlineUsersCount:
    """How many users are connected right now, for the organiser dashboard.

    Authentication only, no permission: the figure is a non-sensitive aggregate
    (no per-user data), and the organiser-only tools page is what scopes who
    actually sees it — role governs UI discovery here, not API access, so there
    is deliberately no hardcoded role check on the endpoint.
    """

    def __init__(
        self,
        presence_gateway: PresenceGateway,
        current_user_provider: CurrentUserProvider,
    ):
        self.presence_gateway = presence_gateway
        self.current_user_provider = current_user_provider

    async def __call__(self) -> OnlineUsersCountOutput:
        await self.current_user_provider.require_user_id()
        count = await self.presence_gateway.count_online()
        return OnlineUsersCountOutput(count=count)
