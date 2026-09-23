import asyncio
from collections.abc import Sequence
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


# Cap on fan-out publishes awaiting their store-ack at once. nats-py has no
# async-publish API with a pending limit, so without one a large fan-out puts
# every publish in flight together: "the client does not bound how many are in
# flight — check every ack, and add your own limit for large bursts"
# (https://docs.nats.io/learn/jetstream/advanced-publishing). NATS gives no
# figure for Python; 100 keeps a fan-out fast without flooding the connection.
_MAX_IN_FLIGHT_PUBLISHES = 100


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

    async def publish_many(self, events: Sequence[AppEvent]) -> None:
        in_flight = asyncio.Semaphore(_MAX_IN_FLIGHT_PUBLISHES)

        async def publish_bounded(event: AppEvent) -> None:
            async with in_flight:
                await self.publish(event)

        # return_exceptions, not a TaskGroup: a TaskGroup would cancel every
        # other publish on the first failure, and a plain gather would return on
        # it while the rest ran on unawaited, their errors lost.
        results = await asyncio.gather(
            *(publish_bounded(event) for event in events), return_exceptions=True
        )
        failures = [result for result in results if isinstance(result, Exception)]
        if failures:
            msg = f"{len(failures)} of {len(events)} events were not published"
            raise ExceptionGroup(msg, failures)

    async def publish_raw(
        self,
        subject: str,
        payload: dict[str, Any],
        message_id: str,
        occurred_at: datetime,
        trace_headers: dict[str, str] | None,
    ) -> None:
        # Publish through JetStream (stream=...) so the call awaits the store
        # ack — the relay only marks a row delivered once NATS confirms it.
        # Nats-Msg-Id lets JetStream dedup a redelivered row within its window.
        await self.broker.publish(
            payload,
            subject=subject,
            stream=_STREAM_NAME,
            headers={
                # Set here, so the broker's tracing middleware keeps them rather
                # than stamping the relay's own (trace-less) context.
                **(trace_headers or {}),
                "Nats-Msg-Id": message_id,
                OCCURRED_AT_HEADER: occurred_at.isoformat(),
            },
            timeout=_PUBLISH_TIMEOUT_SECONDS,
        )
