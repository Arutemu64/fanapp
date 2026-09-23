from datetime import datetime
from typing import Any

from faststream.nats import NatsBroker

from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.base import AppEvent

# Name of the JetStream stream that captures domain-event subjects.
# Mirrors fanfan.presentation.faststream.jstream.stream — kept as a local
# constant so this adapter never imports the presentation layer.
_STREAM_NAME = "stream"

# When the event's transaction committed, as ISO 8601. Read back by consumers
# (presentation/faststream/headers.py) that must not act on a stale event.
OCCURRED_AT_HEADER = "Occurred-At"

# Bound the wait for the JetStream store-ack. publish() otherwise inherits
# nats-py's context timeout, which can be unbounded — and the relay drains
# serially in one loop, so a single publish that never returns silently freezes
# every later drain with no log. A bounded wait raises instead, so the relay logs
# the row as a failed attempt and retries it with backoff.
_PUBLISH_TIMEOUT_SECONDS = 10.0


class NatsEventBroker(EventBroker):
    def __init__(self, broker: NatsBroker) -> None:
        self.broker = broker

    async def publish(self, event: AppEvent) -> None:
        # Through JetStream, like publish_raw: a core publish gets no reply, so
        # an event the stream did not store (subject not captured, connection
        # lost mid-send) would vanish without an error. The PubAck turns that
        # into an exception the caller's consumer redelivers on.
        # https://docs.nats.io/learn/jetstream/publishing
        headers: dict[str, str] = {}
        dedup_id = event.dedup_id()
        if dedup_id is not None:
            headers["Nats-Msg-Id"] = dedup_id
        await self.broker.publish(
            event,
            subject=event.subject,
            stream=_STREAM_NAME,
            headers=headers,
            timeout=_PUBLISH_TIMEOUT_SECONDS,
        )

    async def publish_raw(
        self,
        subject: str,
        payload: dict[str, Any],
        message_id: str,
        occurred_at: datetime,
    ) -> None:
        # Publish through JetStream (stream=...) so the call awaits the store
        # ack — the relay only marks a row delivered once NATS confirms it.
        # Nats-Msg-Id lets JetStream dedup a redelivered row within its window.
        await self.broker.publish(
            payload,
            subject=subject,
            stream=_STREAM_NAME,
            headers={
                "Nats-Msg-Id": message_id,
                OCCURRED_AT_HEADER: occurred_at.isoformat(),
            },
            timeout=_PUBLISH_TIMEOUT_SECONDS,
        )
