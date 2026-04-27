from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.events.users import EmailConfirmationCodeRequestedEvent


class RequestEmailCode:
    def __init__(
        self,
        user_repo: UserRepository,
        event_broker: EventBroker,
        current_user_provider: CurrentUserProvider,
    ):
        self.user_repo = user_repo
        self.event_broker = event_broker
        self.current_user_provider = current_user_provider

    async def __call__(self) -> None:
        current_user = await self.current_user_provider.require_user()

        await self.event_broker.publish(
            EmailConfirmationCodeRequestedEvent(user_id=current_user.id)
        )
