from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from fanfan.adapters.db.models.base import BaseORM
from fanfan.adapters.db.models.mixins.pk import UUIDPrimaryKeyMixin
from fanfan.adapters.db.models.mixins.timestamps import UpdatedAtMixin


class OutboxEventORM(UUIDPrimaryKeyMixin, UpdatedAtMixin, BaseORM):
    """A domain event awaiting delivery to NATS.

    Rows are written inside the same transaction as the aggregate change, then
    delivered by the outbox relay (see presentation/faststream/outbox_relay.py).
    The row id doubles as the NATS dedup id (``Nats-Msg-Id``).
    """

    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "ix_outbox_events_unpublished",
            "created_at",
            postgresql_where="published_at IS NULL",
        ),
        Index("ix_outbox_events_published_at", "published_at"),
    )

    subject: Mapped[str] = mapped_column(Text())
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text())
    trace_headers: Mapped[dict[str, str] | None] = mapped_column(JSONB())
