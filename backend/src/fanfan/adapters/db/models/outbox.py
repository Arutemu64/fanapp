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
        # Serves the retention sweep (delete_published_before), which filters the
        # exact complement of the index above and so could not use it. Without
        # this the cron full-scans the table on every tick, even once there is
        # nothing left to delete.
        Index("ix_outbox_events_published_at", "published_at"),
    )

    subject: Mapped[str] = mapped_column(Text())
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Retry state for rows whose publish failed. A failing row is pushed back to
    # next_attempt_at (NULL = due now) instead of being retried at the head of
    # the queue, so one row NATS keeps rejecting cannot stall every event behind
    # it. The relay filters on it within the partial index's tiny undelivered
    # set, so it needs no index of its own.
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text())
    # Sentry propagation headers of the request or task that wrote the event,
    # forwarded by the relay so the consumer's work joins the producer's trace
    # even though the relay itself runs outside it. NULL when nothing was traced.
    trace_headers: Mapped[dict[str, str] | None] = mapped_column(JSONB())
