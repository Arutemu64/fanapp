from uuid import UUID, uuid7

from sqlalchemy import Index, Uuid, func, select
from sqlalchemy.orm import (
    Mapped,
    column_property,
    declared_attr,
    mapped_column,
)

from fanfan.adapters.db.models.base import UUID_ID_SERVER_DEFAULT, BaseORM
from fanfan.adapters.db.models.mixins.order import OrderMixin


class ScheduleEventORM(BaseORM, OrderMixin):
    __tablename__ = "schedule"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid7,
        server_default=UUID_ID_SERVER_DEFAULT,
    )
    public_id: Mapped[int] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(index=True)
    duration: Mapped[int] = mapped_column(server_default="0")
    is_current: Mapped[bool] = mapped_column(server_default="False")
    is_skipped: Mapped[bool] = mapped_column(server_default="False")
    nomination_title: Mapped[str | None] = mapped_column()
    block_title: Mapped[str | None] = mapped_column()

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

    @declared_attr
    @classmethod
    def queue(cls) -> Mapped[int | None]:
        # Dense 1..N position among non-skipped events (skipped rows -> NULL).
        # Kept as a correlated scalar subquery (not a plain window column) so it
        # can be referenced as an expression in WHERE clauses too, e.g.
        # get_by_queue and the subscription-distance filters. Do not "optimize"
        # it into a single-pass window column without preserving that.
        queue_subquery = (
            select(
                cls.id,
                func.row_number().over(order_by=cls.order).label("queue"),
            )
            .where(cls.is_skipped.isnot(True))
            .subquery()
        )
        stmt = select(queue_subquery.c.queue).where(cls.id == queue_subquery.c.id)
        return column_property(
            stmt.scalar_subquery(),
            expire_on_flush=True,
            deferred=True,
        )

    @declared_attr
    @classmethod
    def time_until(cls) -> Mapped[int | None]:
        stmt = (
            select(
                cls.id,
                func.coalesce(
                    # ROWS frame = "all preceding non-skipped rows". RANGE here
                    # would frame by the float ``order`` value (which has gaps
                    # from place_after averaging) and drop events.
                    func.sum(cls.duration).over(order_by=cls.order, rows=(None, -1)),
                    0,
                ).label("time_until"),
            )
            .where(cls.is_skipped.isnot(True))
            .subquery()
        )

        return column_property(
            select(stmt.c.time_until).where(cls.id == stmt.c.id).scalar_subquery(),
            expire_on_flush=True,
            deferred=True,
        )

    def __str__(self) -> str:
        return self.title
