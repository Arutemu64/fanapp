from collections.abc import Sequence
from datetime import datetime
from typing import Any

from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.base import AppEvent


class FakeEventBroker(EventBroker):
    def __init__(self) -> None:
        # Service events still publish directly (fire-and-forget).
        self.published_events: list[AppEvent] = []
        # Raw publishes, as the outbox relay would emit them.
        self.published_raw: list[tuple[str, dict[str, Any], str]] = []
        # occurred_at of each raw publish, in the same order.
        self.published_occurred_at: list[datetime] = []
        self.published_trace_headers: list[dict[str, str] | None] = []

    async def publish(self, event: AppEvent) -> None:
        self.published_events.append(event)

    async def publish_many(self, events: Sequence[AppEvent]) -> None:
        self.published_events.extend(events)

    async def publish_raw(
        self,
        subject: str,
        payload: dict[str, Any],
        message_id: str,
        occurred_at: datetime,
        trace_headers: dict[str, str] | None,
    ) -> None:
        self.published_raw.append((subject, payload, message_id))
        self.published_occurred_at.append(occurred_at)
        self.published_trace_headers.append(trace_headers)
