from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, undefer

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.mappers.subscription import SubscriptionMapper
from fanfan.adapters.db.models import ScheduleItemORM, SubscriptionORM
from fanfan.application.dto.subscription import SubscriptionFullDTO
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.core.exceptions.schedule import ScheduleItemNotFound
from fanfan.core.exceptions.subscriptions import SubscriptionAlreadyExists
from fanfan.core.models.subscription import (
    Subscription,
)
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


def _select_subscription_full_dto():
    return (
        select(SubscriptionORM)
        .join(ScheduleItemORM)
        .options(
            joinedload(SubscriptionORM.event).options(
                undefer(ScheduleItemORM.queue),
                undefer(ScheduleItemORM.time_until),
            )
        )
    )


class SqlSubscriptionGateway(SubscriptionGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = SubscriptionMapper()

    async def add(self, subscription: Subscription) -> None:
        subscription_orm = self.mapper.from_model(subscription)
        self.session.add(subscription_orm)
        with translate_integrity_error(
            {
                "fk_subscriptions_schedule_item_id_schedule": ScheduleItemNotFound,
                "uq_subscriptions_schedule_item_id": SubscriptionAlreadyExists,
            }
        ):
            await self.session.flush([subscription_orm])

    async def get_by_id(self, subscription_id: SubscriptionId) -> Subscription | None:
        stmt = (
            select(SubscriptionORM)
            .where(SubscriptionORM.id == subscription_id)
            .with_for_update()
        )
        subscription_orm = await self.session.scalar(stmt)
        return self.mapper.to_model(subscription_orm) if subscription_orm else None

    async def delete(self, subscription: Subscription) -> None:
        await self.session.execute(
            delete(SubscriptionORM).where(SubscriptionORM.id == subscription.id)
        )

    # Read projections (return DTOs, not aggregates)
    async def read_upcoming_subscriptions(
        self, current_event_queue: int
    ) -> list[SubscriptionFullDTO]:
        stmt = _select_subscription_full_dto().where(
            # Ignore skipped events
            ScheduleItemORM.is_skipped.isnot(True),
            # Fire once the event is within `counter` positions of the stage.
            SubscriptionORM.counter >= (ScheduleItemORM.queue - current_event_queue),
            # Ignore past events due to previous clause
            (ScheduleItemORM.queue - current_event_queue) >= 0,
        )

        results = await self.session.scalars(stmt)

        return [
            self.mapper.parse_full_dto(subscription_orm) for subscription_orm in results
        ]

    async def read_subscriptions_by_user(
        self, user_id: UserId
    ) -> list[SubscriptionFullDTO]:
        stmt = (
            _select_subscription_full_dto()
            .where(SubscriptionORM.user_id == user_id)
            .order_by(ScheduleItemORM.order)
        )
        results = await self.session.scalars(stmt)
        return [
            self.mapper.parse_full_dto(subscription_orm) for subscription_orm in results
        ]
