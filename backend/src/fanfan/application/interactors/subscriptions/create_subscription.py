import logging

from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.schedule_events import (
    ScheduleEventRepository,
)
from fanfan.application.ports.repositories.subscriptions import (
    SubscriptionRepository,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.models.subscription import Subscription
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.subscription import SubscriptionId

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
        id_provider: IdProvider,
        schedule_repo: ScheduleEventRepository,
        trx: TransactionManager,
    ) -> None:
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo
        self.schedule_repo = schedule_repo
        self.id_provider = id_provider
        self.trx = trx

    async def __call__(
        self,
        data: CreateSubscriptionInput,
    ) -> CreateSubscriptionOutput:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        subscription = Subscription(
            user_id=current_user.id,
            event_id=data.event_id,
            counter=data.counter,
        )
        await self.subscription_repo.add(subscription)
        await self.trx.commit()
        logger.info(
            "Subscription %s created",
            subscription.id,
            extra={"user_subscription": subscription},
        )
        return CreateSubscriptionOutput(subscription_id=subscription.id)
