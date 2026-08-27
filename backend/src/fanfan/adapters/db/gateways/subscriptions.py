from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, undefer

from fanfan.adapters.db.constraints import translate_integrity_error
from fanfan.adapters.db.models import ScheduleEventORM, SubscriptionORM
from fanfan.application.dto.subscription import (
    SubscriptionEventDTO,
    SubscriptionFullDTO,
)
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.exceptions.subscriptions import SubscriptionAlreadyExists
from fanfan.core.models.subscription import (
    Subscription,
)
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


def _from_model(model: Subscription) -> SubscriptionORM:
    return SubscriptionORM(
        id=model.id,
        user_id=model.user_id,
        event_id=model.event_id,
        counter=model.counter,
    )


def _to_model(orm: SubscriptionORM) -> Subscription:
    return Subscription(
        id=SubscriptionId(orm.id),
        user_id=UserId(orm.user_id),
        event_id=ScheduleEventId(orm.event_id),
        counter=orm.counter,
    )


def _parse_full_dto(subscription_orm: SubscriptionORM) -> SubscriptionFullDTO:
    return SubscriptionFullDTO(
        id=SubscriptionId(subscription_orm.id),
        user_id=UserId(subscription_orm.user_id),
        counter=subscription_orm.counter,
        event=SubscriptionEventDTO(
            id=ScheduleEventId(subscription_orm.event.id),
            number=subscription_orm.event.number,
            title=subscription_orm.event.title,
            order=subscription_orm.event.order,
            queue=subscription_orm.event.queue,
        ),
    )


def _select_subscription_full_dto():
    return (
        select(SubscriptionORM)
        .join(ScheduleEventORM)
        .options(
            joinedload(SubscriptionORM.event).options(
                undefer(ScheduleEventORM.queue),
            )
        )
    )


class SqlSubscriptionGateway(SubscriptionGateway):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, subscription: Subscription) -> None:
        subscription_orm = _from_model(subscription)
        self.session.add(subscription_orm)
        with translate_integrity_error(
            {
                "fk_subscriptions_event_id_schedule_events": EventNotFound,
                "uq_subscriptions_event_id": SubscriptionAlreadyExists,
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
        return _to_model(subscription_orm) if subscription_orm else None

    async def delete(self, subscription: Subscription) -> None:
        await self.session.execute(
            delete(SubscriptionORM).where(SubscriptionORM.id == subscription.id)
        )

    async def read_upcoming_subscriptions(
        self, current_event_queue: int
    ) -> list[SubscriptionFullDTO]:
        stmt = _select_subscription_full_dto().where(
            ScheduleEventORM.is_skipped.isnot(True),  # noqa: FBT003
            # Fire once the event is within `counter` positions of the stage.
            SubscriptionORM.counter >= (ScheduleEventORM.queue - current_event_queue),
            # Excludes past events (negative diff); the counter check above
            # doesn't reject those on its own.
            (ScheduleEventORM.queue - current_event_queue) >= 0,
        )

        results = await self.session.scalars(stmt)

        return [_parse_full_dto(subscription_orm) for subscription_orm in results]

    async def read_subscriptions_by_user(
        self, user_id: UserId
    ) -> list[SubscriptionFullDTO]:
        stmt = (
            _select_subscription_full_dto()
            .where(SubscriptionORM.user_id == user_id)
            .order_by(ScheduleEventORM.order)
        )
        results = await self.session.scalars(stmt)
        return [_parse_full_dto(subscription_orm) for subscription_orm in results]
