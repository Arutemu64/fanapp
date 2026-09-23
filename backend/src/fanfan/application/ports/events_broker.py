from datetime import datetime
from typing import Any, Protocol

from fanfan.core.events.base import AppEvent


class EventBroker(Protocol):
    async def publish(self, event: AppEvent) -> None: ...

    async def publish_raw(
        self,
        subject: str,
        payload: dict[str, Any],
        message_id: str,
        occurred_at: datetime,
    ) -> None:
        """Publish an already-serialized event (used by the outbox relay).

        ``message_id`` is sent as the NATS dedup id so re-delivery of the same
        outbox row is collapsed by JetStream within its dedup window.
        ``occurred_at`` travels as a header so a consumer can tell how late the
        event arrives — relay retries and outages can hold it back.
        """
        ...
