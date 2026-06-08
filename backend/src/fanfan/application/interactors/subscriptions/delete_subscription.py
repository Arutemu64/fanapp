import logging

from pydantic import BaseModel

from fanfan.application.ports.repositories.subscriptions import SubscriptionRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.subscriptions import SubscriptionNotFound
from fanfan.core.vo.subscription import SubscriptionId

logger = logging.getLogger(__name__)


class DeleteSubscriptionInput(BaseModel):
    subscription_id: SubscriptionId


class DeleteSubscription:
    def __init__(
        self,
        subscription_repo: SubscriptionRepository,
        user_repo: UserRepository,
        current_user_provider: CurrentUserProvider,
        uow: UnitOfWork,
    ) -> None:
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo
        self.current_user_provider = current_user_provider
        self.uow = uow

    async def __call__(self, data: DeleteSubscriptionInput) -> None:
        current_user = await self.current_user_provider.require_user()
        subscription = await self.subscription_repo.get_by_id(
            subscription_id=data.subscription_id
        )
        if subscription is None:
            raise SubscriptionNotFound
        if subscription.user_id != current_user.id:
            raise AccessDenied
        await self.subscription_repo.delete(subscription)
        await self.uow.commit()
        logger.info(
            "Subscription %s deleted",
            subscription.id,
        )
