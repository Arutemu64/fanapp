from fanfan.application.ports.presence import PresenceGateway
from fanfan.application.services.current_user import CurrentUserProvider


class RecordPresence:
    """Refresh the current user's online marker.

    Called by the SSE route on connect and on each heartbeat tick, so a marker
    stays fresh only while the connection is live. An unauthenticated stream has
    no user to record, so it is a no-op — presence counts real users, not open
    sockets.
    """

    def __init__(
        self,
        presence_gateway: PresenceGateway,
        current_user_provider: CurrentUserProvider,
    ):
        self.presence_gateway = presence_gateway
        self.current_user_provider = current_user_provider

    async def __call__(self) -> None:
        user_id = await self.current_user_provider.get_user_id()
        if user_id is None:
            return
        await self.presence_gateway.mark_online(user_id)
