from datetime import datetime

from faststream.nats import NatsMessage

from fanfan.adapters.nats.events_broker import OCCURRED_AT_HEADER


def read_occurred_at(msg: NatsMessage) -> datetime | None:
    """When the event's transaction committed, or None if the header is absent.

    Only outbox-relayed events carry it; a service event published directly, or
    a message relayed before the header existed, has none.
    """
    raw = msg.headers.get(OCCURRED_AT_HEADER)
    if raw is None:
        return None
    return datetime.fromisoformat(raw)
