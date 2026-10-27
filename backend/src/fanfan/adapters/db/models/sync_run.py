from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin
from fanfan.core.vo.sync import SyncRunStatus, SyncSource


class SyncRunORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    """One execution of a vendor sync, from any trigger (manual, cron or CLI)."""

    __tablename__ = "sync_runs"
    __table_args__ = (
        Index(
            "uq_sync_runs_active",
            "source",
            unique=True,
            postgresql_where="finished_at IS NULL",
        ),
    )

    source: Mapped[SyncSource] = str_enum_column(
        SyncSource,
        name="syncsource",
    )
    status: Mapped[SyncRunStatus] = str_enum_column(
        SyncRunStatus,
        name="syncrunstatus",
    )
    by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    result: Mapped[str | None] = mapped_column(Text())
    error: Mapped[str | None] = mapped_column(Text())
