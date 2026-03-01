from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.events.users import EmailVerificationRequestedEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.users import UserNotFound


class RequestEmailVerification:
    def __init__(
        self,
        user_gateway: UserGateway,
        event_broker: EventBroker,
        id_provider: IdProvider,
    ):
        self.user_gateway = user_gateway
        self.event_broker = event_broker
        self.id_provider = id_provider

    async def __call__(self):
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound

        await self.event_broker.publish(
            EmailVerificationRequestedEvent(user_id=current_user.id)
        )
