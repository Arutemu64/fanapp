from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fanfan.adapters.db.models.base import BaseORM, str_enum_column
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.user import UserORM
from fanfan.core.vo.sync import SyncRunStatus, SyncSource, SyncTrigger


class SyncRunORM(UUIDPrimaryKeyMixin, BaseORM):
    """Append-only audit log of external sync runs — rows never receive
    UPDATEs, so no ``UpdatedAtMixin``."""

    __tablename__ = "sync_runs"

    source: Mapped[SyncSource] = str_enum_column(
        SyncSource,
        name="syncsource",
        index=True,
    )
    trigger: Mapped[SyncTrigger] = str_enum_column(
        SyncTrigger,
        name="synctrigger",
        length=16,
    )
    status: Mapped[SyncRunStatus] = str_enum_column(
        SyncRunStatus,
        name="syncrunstatus",
        length=16,
    )
    started_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column()

    started_by: Mapped[UserORM | None] = relationship(foreign_keys=started_by_user_id)
