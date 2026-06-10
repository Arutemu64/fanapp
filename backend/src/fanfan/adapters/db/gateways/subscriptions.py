from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, undefer

from fanfan.adapters.db.constraints import get_constraint_name
from fanfan.adapters.db.mappers.subscription import SubscriptionMapper
from fanfan.adapters.db.models import ScheduleEventORM, SubscriptionORM
from fanfan.application.dto.subscription import SubscriptionFullDTO
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.exceptions.subscriptions import SubscriptionAlreadyExists
from fanfan.core.models.subscription import (
    Subscription,
)
from fanfan.core.vo.subscription import SubscriptionId


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


class SqlSubscriptionGateway(SubscriptionGateway):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.mapper = SubscriptionMapper()

    async def add(self, subscription: Subscription) -> None:
        subscription_orm = self.mapper.from_model(subscription)
        self.session.add(subscription_orm)
        try:
            await self.session.flush([subscription_orm])
        except IntegrityError as e:
            constraint_name = get_constraint_name(e)
            if constraint_name == "fk_subscriptions_event_id_schedule":
                raise EventNotFound from e
            if constraint_name == "uq_subscriptions_event_id":
                raise SubscriptionAlreadyExists from e
            raise

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
