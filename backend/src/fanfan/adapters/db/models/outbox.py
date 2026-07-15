from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin


class OutboxEventORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    """A domain event awaiting delivery to NATS.

    Rows are written inside the same transaction as the aggregate change, then
    delivered by the outbox relay (see presentation/scheduler). The row id
    doubles as the NATS dedup id (``Nats-Msg-Id``).
    """

    __tablename__ = "outbox_events"
    # Partial index: the relay only ever scans undelivered rows ordered by age,
    # so the hot set stays tiny no matter how big the table grows.
    __table_args__ = (
        Index(
            "ix_outbox_events_unpublished",
            "created_at",
            postgresql_where="published_at IS NULL",
        ),
    )

    subject: Mapped[str] = mapped_column(Text())
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB())
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
