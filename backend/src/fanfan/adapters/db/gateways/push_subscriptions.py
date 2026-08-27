from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import PushSubscriptionORM
from fanfan.application.ports.gateways.push_subscriptions import (
    PushSubscriptionGateway,
)
from fanfan.core.exceptions.push_sub import PushSubscriptionAlreadyExists
from fanfan.core.models.push_subscription import PushSubscription
from fanfan.core.vo.push_subscription import PushSubscriptionId
from fanfan.core.vo.user import UserId


def _from_model(model: PushSubscription) -> PushSubscriptionORM:
    return PushSubscriptionORM(
        id=model.id,
        user_id=model.user_id,
        endpoint=model.endpoint,
        p256dh=model.p256dh,
        auth=model.auth,
    )


def _to_model(orm: PushSubscriptionORM) -> PushSubscription:
    return PushSubscription(
        id=PushSubscriptionId(orm.id),
        user_id=UserId(orm.user_id),
        endpoint=orm.endpoint,
        p256dh=orm.p256dh,
        auth=orm.auth,
    )


class SqlPushSubscriptionGateway(PushSubscriptionGateway):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, model: PushSubscription) -> None:
        push_sub_orm = _from_model(model)
        with translate_integrity_error(
            {
                "uq_push_subscriptions_endpoint": PushSubscriptionAlreadyExists,
            }
        ):
            self.session.add(push_sub_orm)
            await self.session.flush([push_sub_orm])

    async def get_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        stmt = (
            select(PushSubscriptionORM)
            .where(PushSubscriptionORM.endpoint == endpoint)
            .with_for_update()
        )
        push_sub_orm = await self.session.scalar(stmt)
        return _to_model(push_sub_orm) if push_sub_orm else None

    async def exists_for_user(self, user_id: UserId, endpoint: str) -> bool:
        stmt = select(
            exists().where(
                PushSubscriptionORM.user_id == user_id,
                PushSubscriptionORM.endpoint == endpoint,
            )
        )
        return bool(await self.session.scalar(stmt))

    async def list_by_user(self, user_id: UserId) -> list[PushSubscription]:
        stmt = select(PushSubscriptionORM).where(PushSubscriptionORM.user_id == user_id)
        push_sub_orm = await self.session.scalars(stmt)
        return [_to_model(ps) for ps in push_sub_orm]

    async def delete(self, model: PushSubscription) -> None:
        stmt = delete(PushSubscriptionORM).where(PushSubscriptionORM.id == model.id)
        await self.session.execute(stmt)
