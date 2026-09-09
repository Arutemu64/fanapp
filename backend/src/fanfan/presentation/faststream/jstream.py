from datetime import timedelta

from faststream.nats import JStream

# Retention must outlast any realistic consumer outage: the outbox never
# redelivers a row once it is marked published, so events expiring from the
# stream before the FastStream service catches up are lost for good. 24h keeps
# an overnight outage survivable; SSE subjects sharing the stream are ephemeral
# and only cost a little extra storage at this size.
# duplicate_window is the span over which JetStream suppresses a re-published
# Nats-Msg-Id (the outbox row id). It is deliberately NOT stretched to match
# max_age: JetStream tracks every id within the window in memory, and it is only
# the first line of defence — the outbox relay marks acked rows published so it
# rarely re-sends, and consumers are idempotent, which is the actual delivery
# guarantee (see application/interactors/outbox/publish_outbox_events.py). Set to
# the JetStream default explicitly so the ~2 min the relay comment relies on is
# visible here rather than implied; 0/unset would resolve to the same 120s server
# side, and the value must stay below max_age.
stream = JStream(
    name="stream",
    max_age=timedelta(hours=24).total_seconds(),
    duplicate_window=timedelta(minutes=2).total_seconds(),
    subjects=["sse.broadcast.*", "sse.user.*.*"],
)
