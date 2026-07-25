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
    # One active run per source. This is the concurrency guard: it stops a manual
    # sync from overlapping a scheduled one (two full sweeps against the same
    # vendor API), and doubles as the "is a run active?" signal the UI uses to
    # disable the button. A crashed worker leaves a row wedged here forever,
    # which is what SyncRunTracker.reap_stale exists to undo.
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
    # Who triggered the run. Cron and CLI runs carry the seeded system user id,
    # not NULL — a NULL here means only that the user was later deleted, so the
    # two cases stay distinguishable in the audit trail.
    by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Free-form Russian summary shown on the organizer page: a short result on
    # success, the failure reason otherwise. Never parsed.
    result: Mapped[str | None] = mapped_column(Text())
    error: Mapped[str | None] = mapped_column(Text())
