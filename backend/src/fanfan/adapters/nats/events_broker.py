import asyncio
from collections.abc import Sequence
from datetime import datetime
from typing import Any, override

from faststream.nats import NatsBroker

from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.base import Message

_STREAM_NAME = "stream"

OCCURRED_AT_HEADER = "Occurred-At"

_PUBLISH_TIMEOUT_SECONDS = 10.0


_MAX_IN_FLIGHT_PUBLISHES = 100


class NatsEventBroker(EventBroker):
    def __init__(self, broker: NatsBroker) -> None:
        self.broker = broker

    @override
    async def publish(self, event: Message) -> None:
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

    @override
    async def publish_many(self, events: Sequence[Message]) -> None:
        in_flight = asyncio.Semaphore(_MAX_IN_FLIGHT_PUBLISHES)

        async def publish_bounded(event: Message) -> None:
            async with in_flight:
                await self.publish(event)

        results = await asyncio.gather(
            *(publish_bounded(event) for event in events), return_exceptions=True
        )
        failures: list[Exception] = []
        for result in results:
            if isinstance(result, Exception):
                failures.append(result)
            elif isinstance(result, BaseException):
                cancelled = RuntimeError("Publish was cancelled")
                cancelled.__cause__ = result
                failures.append(cancelled)
        if failures:
            msg = f"{len(failures)} of {len(events)} events were not published"
            raise ExceptionGroup(msg, failures)

    @override
    async def publish_raw(
        self,
        subject: str,
        payload: dict[str, Any],
        message_id: str,
        occurred_at: datetime,
        trace_headers: dict[str, str] | None,
    ) -> None:
        await self.broker.publish(
            payload,
            subject=subject,
            stream=_STREAM_NAME,
            headers={
                **(trace_headers or {}),
                "Nats-Msg-Id": message_id,
                OCCURRED_AT_HEADER: occurred_at.isoformat(),
            },
            timeout=_PUBLISH_TIMEOUT_SECONDS,
        )
