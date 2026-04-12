import logging

from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.subscriptions import SubscriptionRepository
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
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
        id_provider: IdProvider,
        trx: TransactionManager,
    ) -> None:
        self.subscription_repo = subscription_repo
        self.user_repo = user_repo
        self.id_provider = id_provider
        self.trx = trx

    async def __call__(self, data: DeleteSubscriptionInput) -> None:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        subscription = await self.subscription_repo.get_by_id(
            subscription_id=data.subscription_id
        )
        if subscription is None:
            raise SubscriptionNotFound
        if subscription.user_id != current_user.id:
            raise AccessDenied
        await self.subscription_repo.delete(subscription)
        await self.trx.commit()
        logger.info(
            "Subscription %s deleted",
            subscription.id,
        )
