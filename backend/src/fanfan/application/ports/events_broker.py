from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

from fanfan.core.events.base import AppEvent


class EventBroker(Protocol):
    async def publish(self, event: AppEvent) -> None: ...

    async def publish_many(self, events: Sequence[AppEvent]) -> None:
        """Publish a fan-out, trying every event even when some fail.

        One failed publish says nothing about the others, so none is cancelled
        or skipped; once all have been tried, the failures are raised together
        as an ExceptionGroup, so the calling consumer is redelivered and reruns
        the fan-out. Events that did land are dropped by their ``dedup_id``.
        """
        ...

    async def publish_raw(
        self,
        subject: str,
        payload: dict[str, Any],
        message_id: str,
        occurred_at: datetime,
        trace_headers: dict[str, str] | None,
    ) -> None:
        """Publish an already-serialized event (used by the outbox relay).

        ``message_id`` is sent as the NATS dedup id so re-delivery of the same
        outbox row is collapsed by JetStream within its dedup window.
        ``occurred_at`` travels as a header so a consumer can tell how late the
        event arrives — relay retries and outages can hold it back.
        ``trace_headers`` carry the producer's trace, so the consumer joins it
        even though the relay publishes from outside that trace.
        """
        ...
