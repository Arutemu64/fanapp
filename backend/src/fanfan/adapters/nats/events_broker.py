from typing import Any

from faststream.nats import NatsBroker

from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.base import AppEvent

# Name of the JetStream stream that captures domain-event subjects.
# Mirrors fanfan.presentation.faststream.jstream.stream — kept as a local
# constant so this adapter never imports the presentation layer.
_STREAM_NAME = "stream"


class NatsEventBroker(EventBroker):
    def __init__(self, broker: NatsBroker):
        self.broker = broker

    async def publish(self, event: AppEvent) -> None:
        await self.broker.publish(event, subject=event.subject)

    async def publish_raw(
        self, subject: str, payload: dict[str, Any], message_id: str
    ) -> None:
        # Publish through JetStream (stream=...) so the call awaits the store
        # ack — the relay only marks a row delivered once NATS confirms it.
        # Nats-Msg-Id lets JetStream dedup a redelivered row within its window.
        await self.broker.publish(
            payload,
            subject=subject,
            stream=_STREAM_NAME,
            headers={"Nats-Msg-Id": message_id},
        )
