from collections.abc import Sequence
from typing import override
from uuid import UUID

from sqlalchemy import Select, delete, or_, select, update
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
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.core.vo.user import UserId


def _change_id_or_none(value: UUID | None) -> ScheduleChangeId | None:
    if value is None:
        return None
    return ScheduleChangeId(value)


def _from_model(model: Subscription) -> SubscriptionORM:
    return SubscriptionORM(
        id=model.id,
        user_id=model.user_id,
        event_id=model.event_id,
        lead_minutes=model.lead_minutes,
        reminded_by_change_id=model.reminded_by_change_id,
    )


def _to_model(orm: SubscriptionORM) -> Subscription:
    return Subscription(
        id=SubscriptionId(orm.id),
        user_id=UserId(orm.user_id),
        event_id=ScheduleEntryId(orm.event_id),
        lead_minutes=orm.lead_minutes,
        reminded_by_change_id=_change_id_or_none(orm.reminded_by_change_id),
    )


def _parse_full_dto(subscription_orm: SubscriptionORM) -> SubscriptionFullDTO:
    return SubscriptionFullDTO(
        id=SubscriptionId(subscription_orm.id),
        user_id=UserId(subscription_orm.user_id),
        lead_minutes=subscription_orm.lead_minutes,
        reminded_by_change_id=_change_id_or_none(
            subscription_orm.reminded_by_change_id
        ),
        event=SubscriptionEventDTO(
            id=ScheduleEntryId(subscription_orm.event.id),
            number=subscription_orm.event.number,
            title=subscription_orm.event.title,
            position=subscription_orm.event.position,
        ),
    )


def _select_subscription_full_dto() -> Select[SubscriptionORM]:
    return (
        select(SubscriptionORM)
        .join(ScheduleEventORM)
        .options(
            joinedload(SubscriptionORM.event).options(
                undefer(ScheduleEventORM.position),
            )
        )
    )


class SqlSubscriptionGateway(SubscriptionGateway):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def add(self, subscription: Subscription) -> None:
        subscription_orm = _from_model(subscription)
        self.session.add(subscription_orm)
        with translate_integrity_error(
            {
                "fk_subscriptions_event_id_schedule": EventNotFound,
                "uq_subscriptions_event_id_user_id": SubscriptionAlreadyExists,
            }
        ):
            await self.session.flush()

    @override
    async def get_by_id(self, subscription_id: SubscriptionId) -> Subscription | None:
        stmt = (
            select(SubscriptionORM)
            .where(SubscriptionORM.id == subscription_id)
            .with_for_update()
        )
        subscription_orm = await self.session.scalar(stmt)
        return _to_model(subscription_orm) if subscription_orm else None

    @override
    async def delete(self, subscription: Subscription) -> None:
        await self.session.execute(
            delete(SubscriptionORM).where(SubscriptionORM.id == subscription.id)
        )

    @override
    async def set_reminded_by(
        self,
        subscription_ids: Sequence[SubscriptionId],
        change_id: ScheduleChangeId | None,
    ) -> None:
        if not subscription_ids:
            return
        await self.session.execute(
            update(SubscriptionORM)
            .where(SubscriptionORM.id.in_(subscription_ids))
            .values(reminded_by_change_id=change_id)
        )

    @override
    async def read_subscriptions_to_notify(
        self,
        current_event_position: int | None,
        changed_event_id: ScheduleEntryId,
    ) -> list[SubscriptionFullDTO]:
        is_changed_event = SubscriptionORM.event_id == changed_event_id
        if current_event_position is None:
            stmt = _select_subscription_full_dto().where(is_changed_event)
        else:
            stmt = _select_subscription_full_dto().where(
                or_(
                    ScheduleEventORM.position >= current_event_position,
                    is_changed_event,
                )
            )
        results = await self.session.scalars(stmt)
        return [_parse_full_dto(subscription_orm) for subscription_orm in results]

    @override
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
