from collections.abc import Sequence
from datetime import datetime
from typing import Any, override

from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.base import Message


class FakeEventBroker(EventBroker):
    def __init__(self) -> None:
        self.published_events: list[Message] = []
        self.published_raw: list[tuple[str, dict[str, Any], str]] = []
        self.published_occurred_at: list[datetime] = []
        self.published_trace_headers: list[dict[str, str] | None] = []

    @override
    async def publish(self, event: Message) -> None:
        self.published_events.append(event)

    @override
    async def publish_many(self, events: Sequence[Message]) -> None:
        self.published_events.extend(events)

    @override
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
