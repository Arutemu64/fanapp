from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OutboxMessage(BaseModel):
    """An undelivered outbox row, as read by the relay."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject: str
    payload: dict[str, Any]
    # The commit timestamp of the transaction that wrote the event.
    created_at: datetime
    # Trace propagation headers of the producer, forwarded to the consumer.
    trace_headers: dict[str, str] | None
    # Failed publish attempts so far.
    attempts: int
