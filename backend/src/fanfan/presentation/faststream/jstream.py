import dataclasses
import logging
from datetime import timedelta

from faststream.nats import JStream, NatsBroker
from nats.js.api import DiscardPolicy

logger = logging.getLogger(__name__)

stream = JStream(
    name="stream",
    max_age=timedelta(hours=24).total_seconds(),
    duplicate_window=timedelta(minutes=2).total_seconds(),
    max_bytes=256 * 1024 * 1024,
    discard=DiscardPolicy.NEW,
)

scheduler_stream = JStream(
    name="scheduler",
    subjects=["scheduler.schedule.*"],
    max_msgs_per_subject=1,
    allow_msg_schedules=True,
)

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
