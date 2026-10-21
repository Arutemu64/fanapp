import dataclasses
import logging
from datetime import timedelta

from faststream.nats import JStream, NatsBroker
from nats.js.api import DiscardPolicy

logger = logging.getLogger(__name__)

# Retention must outlast any realistic consumer outage: the outbox never
# redelivers a row once it is marked published, so events expiring from the
# stream before the FastStream service catches up are lost for good. 24h keeps
# an overnight outage survivable.
# duplicate_window is the span over which JetStream suppresses a re-published
# Nats-Msg-Id (the outbox row id). It is deliberately NOT stretched to match
# max_age: JetStream tracks every id within the window in memory, and it is only
# the first line of defence — the outbox relay marks acked rows published so it
# rarely re-sends, and consumers are idempotent, which is the actual delivery
# guarantee (see application/interactors/outbox/publish_outbox_events.py). Set to
# the JetStream default explicitly so the ~2 min the relay comment relies on is
# visible here rather than implied; 0/unset would resolve to the same 120s server
# side, and the value must stay below max_age.
# max_bytes caps the disk a runaway publisher can take, far above a day of real
# traffic and below the server's max_file_store (docker-compose.yml nats-conf).
# DiscardPolicy.NEW rejects a publish into a full stream instead of dropping the
# oldest message, which may be an event no consumer has read yet: the rejected
# publish fails, so the outbox keeps the row and retries it.
# https://docs.nats.io/reference/jetstream/api/stream/create
# The SSE subjects stay out: they go over core NATS (adapters/nats/
# realtime_gateway.py) and nothing replays them, so storing them only costs disk.
stream = JStream(
    name="stream",
    max_age=timedelta(hours=24).total_seconds(),
    duplicate_window=timedelta(minutes=2).total_seconds(),
    max_bytes=256 * 1024 * 1024,
    discard=DiscardPolicy.NEW,
)

# Subjects the stream once captured. FastStream keeps every subject the server
# already has when it updates a stream, so dropping one from the declaration
# leaves it captured until it is removed here.
# TODO: delete once production has started on this build — the removal is
# then on its NATS volume, and fresh deployments never had these subjects.
_RETIRED_SUBJECTS = frozenset({"sse.broadcast.*", "sse.user.*.*"})


async def retire_stream_subjects(broker: NatsBroker) -> None:
    js = broker.connection.jetstream()
    info = await js.stream_info(stream.name)
    current = info.config.subjects or []
    kept = [subject for subject in current if subject not in _RETIRED_SUBJECTS]
    if kept == current:
        return
    await js.update_stream(config=dataclasses.replace(info.config, subjects=kept))
    logger.info(
        "Retired stream subjects",
        extra={"subjects": ",".join(sorted(set(current) - set(kept)))},
    )
