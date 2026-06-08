import logging

from pydantic import BaseModel

from fanfan.application.ports.repositories.schedule_events import (
    ScheduleEventRepository,
)
from fanfan.application.ports.repositories.subscriptions import (
    SubscriptionRepository,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.models.subscription import Subscription
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.subscription import SubscriptionId, generate_subscription_id

logger = logging.getLogger(__name__)


class CreateSubscriptionInput(BaseModel):
    event_id: ScheduleEventId
    counter: int


class CreateSubscriptionOutput(BaseModel):
    subscription_id: SubscriptionId


class CreateSubscription:
    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        user_repo: UserRepository,
        current_user_provider: CurrentUserProvider,
        schedule_repo: ScheduleEventRepository,
        uow: UnitOfWork,
    ) -> None:
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo
        self.schedule_repo = schedule_repo
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(
        self,
        data: CreateSubscriptionInput,
    ) -> CreateSubscriptionOutput:
        current_user = await self.current_user_provider.require_user()
        subscription = Subscription(
            id=generate_subscription_id(),
            user_id=current_user.id,
            event_id=data.event_id,
            counter=data.counter,
        )
        await self.subscription_repo.add(subscription)
        await self.uow.commit()
        logger.info(
            "Subscription %s created",
            subscription.id,
            extra={"user_subscription": subscription},
        )
        return CreateSubscriptionOutput(subscription_id=subscription.id)
