from datetime import timedelta

from faststream.nats import JStream

# Retention must outlast any realistic consumer outage: the outbox never
# redelivers a row once it is marked published, so events expiring from the
# stream before the FastStream service catches up are lost for good. 24h keeps
# an overnight outage survivable; SSE subjects sharing the stream are ephemeral
# and only cost a little extra storage at this size.
stream = JStream(
    name="stream",
    max_age=timedelta(hours=24).total_seconds(),
    subjects=["sse.broadcast.*", "sse.user.*.*"],
)
