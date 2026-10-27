from typing import override

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

    number: Mapped[int | None] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column()
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
        CheckConstraint(
            "type = 'event' OR "
            "(number IS NULL AND is_current IS FALSE AND is_skipped IS FALSE)",
            name="block_start_has_no_stage_state",
        ),
        *OrderMixin.order_table_args(),
    )
    __mapper_args__ = {"polymorphic_on": "type"}  # noqa: RUF012

    @override
    def __str__(self) -> str:
        return self.title


class ScheduleEventORM(ScheduleEntryORM):
    __tablename__ = None
    __mapper_args__ = {"polymorphic_identity": ScheduleEntryType.EVENT}  # noqa: RUF012

    @classmethod
    def ranking_subquery(cls) -> Subquery:
        return (
            select(
                cls.id,
                func.row_number().over(order_by=cls.order).label("position"),
            )
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
