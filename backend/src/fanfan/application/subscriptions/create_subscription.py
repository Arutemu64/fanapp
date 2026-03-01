import logging

from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from fanfan.adapters.db.gateways.schedule_events import ScheduleEventGateway
from fanfan.adapters.db.gateways.subscriptions import (
    SubscriptionGateway,
)
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.dto.subscription import SubscriptionFullDTO
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.exceptions.subscriptions import SubscriptionAlreadyExist
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.subscription import (
    Subscription,
)
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class CreateSubscriptionCommand(BaseModel):
    event_id: ScheduleEventId
    counter: int


class CreateSubscription:
    def __init__(
        self,
        subscription_gateway: SubscriptionGateway,
        user_gateway: UserGateway,
        id_provider: IdProvider,
        schedule_gateway: ScheduleEventGateway,
        uow: UnitOfWork,
    ) -> None:
        self.subscription_gateway = subscription_gateway
        self.user_gateway = user_gateway
        self.schedule_gateway = schedule_gateway
        self.id_provider = id_provider
        self.uow = uow

    async def __call__(
        self,
        data: CreateSubscriptionCommand,
    ) -> SubscriptionFullDTO:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            try:
                subscription = await self.subscription_gateway.add_subscription(
                    Subscription(
                        user_id=current_user_id,
                        event_id=data.event_id,
                        counter=data.counter,
                    )
                )
                await self.uow.commit()
            except IntegrityError as e:
                await self.uow.rollback()
                if await self.schedule_gateway.read_event_by_id(data.event_id) is None:
                    raise EventNotFound(event_id=data.event_id) from e
                raise SubscriptionAlreadyExist from e
            else:
                logger.info(
                    "Subscription %s created",
                    subscription.id,
                    extra={"user_subscription": subscription},
                )
                return await self.subscription_gateway.read_user_subscription(
                    subscription.id
                )
