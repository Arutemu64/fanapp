from datetime import datetime

from sqlalchemy import DateTime, Index, func, select, text
from sqlalchemy.orm import (
    Mapped,
    column_property,
    declared_attr,
    mapped_column,
)

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.order import OrderMixin
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin


class ScheduleEventORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, OrderMixin, BaseORM):
    __tablename__ = "schedule_events"

    number: Mapped[int] = mapped_column(unique=True)
    # Not indexed: nothing filters or sorts on title. Reads go by id, queue,
    # order or is_current.
    title: Mapped[str] = mapped_column()
    duration_seconds: Mapped[int] = mapped_column(server_default=text("0"))
    is_current: Mapped[bool] = mapped_column(server_default=text("false"))
    is_skipped: Mapped[bool] = mapped_column(server_default=text("false"))
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
        # dense 1..N ``queue`` position. This is the one source of truth for the
        # ranking: the ``queue`` column_property correlates it per row (cheap for
        # single-row reads and reusable as a WHERE expression in get_by_queue /
        # subscription-distance filters), while the schedule list query joins it
        # once to avoid re-running it per row. Absolute event times are no longer
        # derived here — they depend on wall-clock ``now`` and live in the
        # schedule timing application service (see ADR-0008).
        return (
            select(
                cls.id,
                func.row_number().over(order_by=cls.order).label("queue"),
            )
            .where(cls.is_skipped.isnot(True))  # noqa: FBT003
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

    def __str__(self) -> str:
        return self.title
