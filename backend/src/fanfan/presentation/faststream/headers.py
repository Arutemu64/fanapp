from datetime import datetime

from faststream.nats import NatsMessage

from fanfan.adapters.nats.events_broker import OCCURRED_AT_HEADER


def read_occurred_at(msg: NatsMessage) -> datetime:
    """When the event's transaction committed.

    Only outbox-relayed events carry it, so read it only from one of those.
    """
    raw = msg.headers.get(OCCURRED_AT_HEADER)
    if raw is None:
        detail = f"{OCCURRED_AT_HEADER} header missing; was this relayed by the outbox?"
        raise ValueError(detail)
    return datetime.fromisoformat(raw)
