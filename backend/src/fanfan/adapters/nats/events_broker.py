from typing import Any

from faststream.nats import NatsBroker

from fanfan.application.ports.events_broker import EventBroker
from fanfan.core.events.base import AppEvent

# Name of the JetStream stream that captures domain-event subjects.
# Mirrors fanfan.presentation.faststream.jstream.stream — kept as a local
# constant so this adapter never imports the presentation layer.
_STREAM_NAME = "stream"

# Bound the wait for the JetStream store-ack. publish() otherwise inherits
# nats-py's context timeout, which can be unbounded — and the relay runs under
# APScheduler max_instances=1, so a single publish that never returns silently
# freezes every later tick with no log. A bounded wait raises instead, so the
# tick fails loudly and retries next interval.
_PUBLISH_TIMEOUT_SECONDS = 10.0


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
            timeout=_PUBLISH_TIMEOUT_SECONDS,
        )
