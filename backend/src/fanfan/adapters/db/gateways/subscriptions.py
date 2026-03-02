from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, undefer

from fanfan.adapters.db.mappers.subscription import SubscriptionMapper
from fanfan.adapters.db.models import ScheduleEventORM, SubscriptionORM
from fanfan.core.dto.subscription import SubscriptionFullDTO
from fanfan.core.models.subscription import (
    Subscription,
)
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


def _select_subscription_full_dto():
    return (
        select(SubscriptionORM)
        .join(ScheduleEventORM)
        .options(
            joinedload(SubscriptionORM.event).options(
                undefer(ScheduleEventORM.queue),
                undefer(ScheduleEventORM.time_until),
            )
        )
    )


class SubscriptionGateway:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = SubscriptionMapper()

    async def add_subscription(self, subscription: Subscription) -> None:
        subscription_orm = self.mapper.from_model(subscription)
        self.session.add(subscription_orm)

    async def get_subscription_by_id(
        self, subscription_id: SubscriptionId
    ) -> Subscription | None:
        stmt = select(SubscriptionORM).where(SubscriptionORM.id == subscription_id)
        subscription_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(subscription_orm) if subscription_orm else None

    async def get_user_subscription_by_event(
        self, user_id: UserId, event_id: ScheduleEventId
    ) -> Subscription | None:
        stmt = select(SubscriptionORM).where(
            and_(
                SubscriptionORM.user_id == user_id,
                SubscriptionORM.event_id == event_id,
            )
        )
        subscription_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(subscription_orm) if subscription_orm else None

    async def delete_subscription(self, subscription: Subscription) -> None:
        await self.session.execute(
            delete(SubscriptionORM).where(SubscriptionORM.id == subscription.id)
        )

    async def read_user_subscription(
        self, subscription_id: SubscriptionId
    ) -> SubscriptionFullDTO | None:
        stmt = _select_subscription_full_dto().where(
            SubscriptionORM.id == subscription_id
        )

        subscription_orm = await self.session.scalar(stmt)

        return (
            self.mapper.parse_full_dto(subscription_orm) if subscription_orm else None
        )

    async def read_upcoming_subscriptions(
        self, current_event_queue: int
    ) -> list[SubscriptionFullDTO]:
        stmt = _select_subscription_full_dto().where(
            # Ignore skipped events
            ScheduleEventORM.is_skipped.isnot(True),
            # Counter clause
            SubscriptionORM.counter >= (ScheduleEventORM.queue - current_event_queue),
            # Ignore past events due to previous clause
            (ScheduleEventORM.queue - current_event_queue) >= 0,
        )

        results = await self.session.scalars(stmt)

        return [
            self.mapper.parse_full_dto(subscription_orm) for subscription_orm in results
        ]
