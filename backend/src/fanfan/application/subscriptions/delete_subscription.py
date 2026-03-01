import logging

from pydantic import BaseModel

from fanfan.adapters.db.gateways.subscriptions import SubscriptionGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.subscriptions import SubscriptionNotFound
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.vo.subscription import SubscriptionId

logger = logging.getLogger(__name__)


class DeleteSubscriptionCommand(BaseModel):
    subscription_id: SubscriptionId


class DeleteSubscription:
    def __init__(
        self,
        subscription_gateway: SubscriptionGateway,
        user_gateway: UserGateway,
        id_provider: IdProvider,
        uow: UnitOfWork,
    ) -> None:
        self.subscription_gateway = subscription_gateway
        self.user_gateway = user_gateway
        self.id_provider = id_provider
        self.uow = uow

    async def __call__(self, data: DeleteSubscriptionCommand) -> None:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            subscription = await self.subscription_gateway.get_subscription_by_id(
                subscription_id=data.subscription_id
            )
            if subscription is None:
                raise SubscriptionNotFound
            if subscription.user_id != current_user.id:
                raise AccessDenied
            await self.subscription_gateway.delete_subscription(subscription)
            await self.uow.commit()
            logger.info(
                "Subscription %s deleted",
                subscription.id,
                extra={"user_subscription": subscription},
            )
