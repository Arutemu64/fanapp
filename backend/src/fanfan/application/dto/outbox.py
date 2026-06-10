from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OutboxMessage(BaseModel):
    """An undelivered outbox row, as read by the relay."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subject: str
    payload: dict[str, Any]
