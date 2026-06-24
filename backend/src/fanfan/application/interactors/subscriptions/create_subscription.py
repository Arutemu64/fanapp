import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.schedule_items import (
    ScheduleItemGateway,
)
from fanfan.application.ports.gateways.subscriptions import (
    SubscriptionGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.models.subscription import Subscription
from fanfan.core.vo.schedule_item import ScheduleItemId
from fanfan.core.vo.subscription import SubscriptionId, generate_subscription_id

logger = logging.getLogger(__name__)


class CreateSubscriptionInput(BaseModel):
    schedule_item_id: ScheduleItemId
    counter: int


class CreateSubscriptionOutput(BaseModel):
    subscription_id: SubscriptionId


class CreateSubscription:
    def __init__(
        self,
        subscription_gateway: SubscriptionGateway,
        user_gateway: UserGateway,
        current_user_provider: CurrentUserProvider,
        schedule_gateway: ScheduleItemGateway,
        uow: UnitOfWork,
    ) -> None:
        self.subscription_gateway = subscription_gateway
        self.user_gateway = user_gateway
        self.schedule_gateway = schedule_gateway
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
            schedule_item_id=data.schedule_item_id,
            counter=data.counter,
        )
        await self.subscription_gateway.add(subscription)
        await self.uow.commit()
        logger.info(
            "Subscription created",
            extra={
                "subscription_id": str(subscription.id),
                "actor_id": str(current_user.id),
                "schedule_item_id": str(subscription.schedule_item_id),
            },
        )
        return CreateSubscriptionOutput(subscription_id=subscription.id)
