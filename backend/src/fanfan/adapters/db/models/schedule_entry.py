from sqlalchemy import CheckConstraint, Index, func, select, text
from sqlalchemy.orm import (
    Mapped,
    column_property,
    declared_attr,
    mapped_column,
)
from sqlalchemy.sql import Subquery

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.order import OrderMixin
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.core.vo.schedule_entry import ScheduleEntryType


class ScheduleEntryORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, OrderMixin, BaseORM):
    """One row of the programme, loaded as the subclass its ``type`` names.

    Single-table inheritance: querying ScheduleEventORM adds ``type = 'event'``
    on its own, so an events-only read cannot let a block start through
    (https://docs.sqlalchemy.org/en/20/orm/inheritance.html#single-table-inheritance).
    Every column stays declared here, not on the subclass that uses it: the
    index and the check constraint below are table-level and name them, and a
    block start's row still holds them, at the bare values that constraint
    requires.
    """

    __tablename__ = "schedule"

    type: Mapped[ScheduleEntryType] = str_enum_column(
        ScheduleEntryType, name="scheduleentrytype"
    )

    # Nullable: breaks and other filler rows carry no public number. Postgres
    # treats NULLs as distinct in a unique index, so any number of numberless
    # entries coexist while real numbers stay unique.
    number: Mapped[int | None] = mapped_column(unique=True)
    # Not indexed: nothing filters or sorts on title. Reads go by id, position,
    # order or is_current.
    title: Mapped[str] = mapped_column()
    # Seconds, never minutes — sub-minute acts exist, and rounding a per-event
    # duration would accumulate error across the programme.
    duration: Mapped[int] = mapped_column(server_default=text("0"))
    is_current: Mapped[bool] = mapped_column(server_default=text("false"))
    is_skipped: Mapped[bool] = mapped_column(server_default=text("false"))
    nomination_title: Mapped[str | None] = mapped_column()

    __table_args__ = (
        Index(
            "ix_only_one_current",
            "is_current",
            unique=True,
            postgresql_where=(is_current.is_(True)),
        ),
        # A block start is a heading, never a stage act, so it can never be the
        # current or a skipped row, nor hold a public number.
        CheckConstraint(
            "type = 'event' OR "
            "(number IS NULL AND is_current IS FALSE AND is_skipped IS FALSE)",
            name="block_start_has_no_stage_state",
        ),
        # OrderMixin declares its own __table_args__; SQLAlchemy does not merge
        # it with ours, so splice in the deferred order constraint explicitly.
        *OrderMixin.order_table_args(),
    )
    __mapper_args__ = {"polymorphic_on": "type"}  # noqa: RUF012

    def __str__(self) -> str:
        return self.title


class ScheduleEventORM(ScheduleEntryORM):
    # None rather than inherited: the mixins' declared __table_args__ would
    # otherwise make declarative build this subclass a table of its own.
    __tablename__ = None
    __mapper_args__ = {"polymorphic_identity": ScheduleEntryType.EVENT}  # noqa: RUF012

    @classmethod
    def ranking_subquery(cls) -> Subquery:
        # Single window pass over the non-skipped events (block starts take no
        # place), producing each row's dense 1..N ``position`` in the running
        # order. This is the one source of truth for the ranking: the
        # ``position`` column_property correlates it per row (cheap for
        # single-row reads and reusable as a WHERE expression in the
        # subscription-distance filters), while the schedule list query joins it
        # once to avoid re-running it per row.
        return (
            select(
                cls.id,
                func.row_number().over(order_by=cls.order).label("position"),
            )
            # Spelled out: ``position`` below builds this while the class is still
            # being mapped, before SQLAlchemy can add the subclass's ``type``
            # criterion itself.
            .where(
                cls.type == ScheduleEntryType.EVENT,
                cls.is_skipped.isnot(True),  # noqa: FBT003
            )
            .subquery()
        )

    @declared_attr
    @classmethod
    def position(cls) -> Mapped[int | None]:
        ranked = cls.ranking_subquery()
        stmt = select(ranked.c.position).where(cls.id == ranked.c.id)
        # column_property() is typed as MappedSQLExpression[Any]; the declared
        # Mapped[int | None] is the contract SQLAlchemy honours at mapping time.
        return column_property(  # ty: ignore[unsound-return-statement]
            stmt.scalar_subquery(),
            expire_on_flush=True,
            deferred=True,
        )


class ScheduleBlockStartORM(ScheduleEntryORM):
    __tablename__ = None
    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": ScheduleEntryType.BLOCK_START
    }
