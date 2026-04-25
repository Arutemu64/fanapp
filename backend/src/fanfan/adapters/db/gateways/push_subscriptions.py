from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import get_constraint_name
from fanfan.adapters.db.mappers.push_subscription import PushSubscriptionMapper
from fanfan.adapters.db.models import PushSubscriptionORM
from fanfan.application.ports.repositories.push_subscriptions import (
    PushSubscriptionRepository,
)
from fanfan.core.exceptions.push_sub import PushSubscriptionAlreadyExists
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.vo.user import UserId


class SqlPushSubscriptionGateway(PushSubscriptionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = PushSubscriptionMapper()

    async def add(self, model: PushSubscription) -> None:
        push_sub_orm = self.mapper.from_model(model)
        try:
            self.session.add(push_sub_orm)
            await self.session.flush([push_sub_orm])
        except IntegrityError as e:
            constraint_name = get_constraint_name(e)
            if constraint_name == "uq_push_subs_endpoint":
                raise PushSubscriptionAlreadyExists from e
            raise

    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        stmt = (
            select(PushSubscriptionORM)
            .where(PushSubscriptionORM.endpoint == endpoint)
            .with_for_update()
        )
        push_sub_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(push_sub_orm) if push_sub_orm else None

    async def list_by_user(self, user_id: UserId) -> list[PushSubscription]:
        stmt = select(PushSubscriptionORM).where(PushSubscriptionORM.user_id == user_id)
        push_sub_orm = await self.session.scalars(stmt)
        return [self.mapper.to_model(ps) for ps in push_sub_orm]

    async def delete(self, model: PushSubscription) -> None:
        stmt = delete(PushSubscriptionORM).where(PushSubscriptionORM.id == model.id)
        await self.session.execute(stmt)
        return
