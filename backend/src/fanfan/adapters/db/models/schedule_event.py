from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import DateTime, Index, Uuid, func, select
from sqlalchemy.orm import (
    Mapped,
    column_property,
    declared_attr,
    mapped_column,
)

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.order import OrderMixin


class ScheduleEventORM(BaseORM, OrderMixin):
    __tablename__ = "schedule"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )
    number: Mapped[int] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(index=True)
    duration: Mapped[int] = mapped_column(server_default="0")
    is_current: Mapped[bool] = mapped_column(server_default="False")
    is_skipped: Mapped[bool] = mapped_column(server_default="False")
    nomination_title: Mapped[str | None] = mapped_column()
    block_title: Mapped[str | None] = mapped_column()
    # Timezone-aware anchor for drift-aware projection (ADR-0008); we store and
    # compare in UTC, so the column must be tz-aware to avoid naive/aware mixups.
    actual_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "ix_only_one_current",
            "is_current",
            unique=True,
            postgresql_where=(is_current.is_(True)),
        ),
        # OrderMixin declares its own __table_args__; SQLAlchemy does not merge
        # it with ours, so splice in the deferred order constraint explicitly.
        *OrderMixin.order_table_args(),
    )

    @classmethod
    def ranking_subquery(cls):
        # Single window pass over the non-skipped events, producing each row's
        # dense 1..N ``queue`` position and cumulative ``time_until`` (sum of all
        # preceding non-skipped durations). This is the one source of truth for
        # the ranking logic: the queue/time_until column_properties correlate it
        # per row (cheap for single-row reads and reusable as a WHERE expression
        # in get_by_queue / subscription-distance filters), while the schedule
        # list query joins it once to avoid re-running it per row.
        #
        # ROWS frame = "all preceding non-skipped rows". A RANGE frame would
        # frame by the float ``order`` value (which has gaps from place_after
        # averaging) and drop events.
        return (
            select(
                cls.id,
                func.row_number().over(order_by=cls.order).label("queue"),
                func.coalesce(
                    func.sum(cls.duration).over(order_by=cls.order, rows=(None, -1)),
                    0,
                ).label("time_until"),
            )
            .where(cls.is_skipped.isnot(True))
            .subquery()
        )

    @declared_attr
    @classmethod
    def queue(cls) -> Mapped[int | None]:
        ranked = cls.ranking_subquery()
        stmt = select(ranked.c.queue).where(cls.id == ranked.c.id)
        return column_property(
            stmt.scalar_subquery(),
            expire_on_flush=True,
            deferred=True,
        )

    @declared_attr
    @classmethod
    def time_until(cls) -> Mapped[int | None]:
        ranked = cls.ranking_subquery()
        stmt = select(ranked.c.time_until).where(cls.id == ranked.c.id)
        return column_property(
            stmt.scalar_subquery(),
            expire_on_flush=True,
            deferred=True,
        )

    def __str__(self) -> str:
        return self.title
