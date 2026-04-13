from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.core.events.users import EmailConfirmationCodeRequestedEvent


class RequestEmailCode:
    def __init__(
        self,
        user_repo: UserRepository,
        event_broker: EventBroker,
        id_provider: IdProvider,
    ):
        self.user_repo = user_repo
        self.event_broker = event_broker
        self.id_provider = id_provider

    async def __call__(self) -> None:
        current_user = await get_current_user(
            id_provider=self.id_provider, user_repo=self.user_repo
        )

        await self.event_broker.publish(
            EmailConfirmationCodeRequestedEvent(user_id=current_user.id)
        )