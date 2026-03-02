from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import PushSubscriptionORM
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.vo.user import UserId


class PushSubscriptionGateway:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_push_subscription(self, model: PushSubscription) -> PushSubscription:
        push_subscription_orm = PushSubscriptionORM.from_model(model)
        self.session.add(push_subscription_orm)
        await self.session.flush([push_subscription_orm])
        return push_subscription_orm.to_model()

    async def get_push_sub_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        stmt = (
            select(PushSubscriptionORM)
            .where(PushSubscriptionORM.endpoint == endpoint)
            .with_for_update()
        )
        push_subs_orm = await self.session.scalar(stmt)
        return push_subs_orm.to_model() if push_subs_orm else None

    async def list_user_push_subs(self, user_id: UserId) -> list[PushSubscription]:
        stmt = select(PushSubscriptionORM).where(PushSubscriptionORM.user_id == user_id)
        push_subs_orm = await self.session.scalars(stmt)
        return [ps.to_model() for ps in push_subs_orm]

    async def delete_push_subscription(self, model: PushSubscription) -> None:
        stmt = delete(PushSubscriptionORM).where(PushSubscriptionORM.id == model.id)
        await self.session.execute(stmt)
