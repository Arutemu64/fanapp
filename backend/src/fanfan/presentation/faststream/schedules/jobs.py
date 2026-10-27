import logging
from dataclasses import dataclass
from typing import Any

from faststream.nats import NatsBroker
from nats.errors import Error as NatsError
from nats.js.client import JetStreamContext
from nats.js.errors import NotFoundError

from fanfan.application.interactors.notifications.purge_notifications import (
    PurgeNotifications,
)
from fanfan.application.interactors.outbox.purge_outbox_events import (
    PurgeOutboxEvents,
)
from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.interactors.sync.execute_tickets_sync import ExecuteTicketsSync
from fanfan.presentation.faststream.jstream import scheduler_stream
from fanfan.presentation.faststream.schedules.config import SchedulerConfig

logger = logging.getLogger(__name__)

_CRONTAB_FIELDS = 5


@dataclass(frozen=True, slots=True)
class ScheduledJob:
    id: str
    interactor: type[Any]

    @property
    def schedule_subject(self) -> str:
        return f"scheduler.schedule.{self.id}"

    @property
    def tick_subject(self) -> str:
        return f"scheduler.tick.{self.id}"


SYNC_TCLOUD = ScheduledJob("sync_tcloud", ExecuteTicketsSync)
SYNC_COSPLAY2 = ScheduledJob("sync_cosplay2", ExecuteCosplaySync)
OUTBOX_RETENTION = ScheduledJob("outbox_retention", PurgeOutboxEvents)
NOTIFICATION_RETENTION = ScheduledJob("notification_retention", PurgeNotifications)

SCHEDULED_JOBS = (SYNC_TCLOUD, SYNC_COSPLAY2, OUTBOX_RETENTION, NOTIFICATION_RETENTION)


def scheduled_crons(config: SchedulerConfig) -> dict[ScheduledJob, str | None]:
    return {
        SYNC_TCLOUD: config.sync_tcloud_cron,
        SYNC_COSPLAY2: config.sync_cosplay2_cron,
        OUTBOX_RETENTION: config.outbox_retention_cron,
        NOTIFICATION_RETENTION: config.notification_retention_cron,
    }


def schedule_headers(job: ScheduledJob, cron: str, timezone: str) -> dict[str, str]:
    """The headers that make a message on the schedule subject a NATS schedule.

    The env keys predate NATS scheduling and hold five-field crontab, which the
    server rejects as an invalid pattern, so those get a zero seconds field.
    The server refuses a time zone on an interval or one-shot schedule.
    https://github.com/nats-io/nats-architecture-and-design/blob/main/adr/ADR-51.md
    """
    fields = cron.split()
    if len(fields) == _CRONTAB_FIELDS:
        cron = " ".join(["0", *fields])
    headers = {"Nats-Schedule": cron, "Nats-Schedule-Target": job.tick_subject}
    if not cron.startswith(("@every", "@at")):
        headers["Nats-Schedule-Time-Zone"] = timezone
    return headers


async def sync_schedules(
    broker: NatsBroker, config: SchedulerConfig, timezone: str
) -> None:
    """Make the server's schedules match the configured crons.

    A schedule lives on the server and fires whether or not a worker is up, so
    a disabled job is purged rather than merely left unsubscribed. A job that
    fails to schedule (a malformed cron) is logged and unscheduled too, rather
    than left firing on a cron the config no longer holds; it must not keep the
    worker, and with it every other consumer, from starting.
    """
    js = broker.connection.jetstream()
    for job, cron in scheduled_crons(config).items():
        if cron is None:
            await _unschedule(js, job)
            continue
        headers = schedule_headers(job, cron, timezone)
        if await _current_schedule(js, job) == headers:
            continue
        try:
            await js.publish(
                job.schedule_subject,
                stream=scheduler_stream.name,
                headers=headers,
            )
        except NatsError:
            logger.exception(
                "Could not schedule job", extra={"job": job.id, "cron": cron}
            )
            await _unschedule(js, job)
            continue
        logger.info("Job scheduled", extra={"job": job.id, "cron": cron})


async def _unschedule(js: JetStreamContext, job: ScheduledJob) -> None:
    await js.purge_stream(scheduler_stream.name, subject=job.schedule_subject)
    await js.purge_stream(scheduler_stream.name, subject=job.tick_subject)


async def _current_schedule(js: JetStreamContext, job: ScheduledJob) -> dict[str, str]:
    """The schedule headers stored for a job, empty when it has none.

    Filtered to the Nats-Schedule* keys because the server adds its own, such
    as the Nats-Rollup it applies to every schedule.
    """
    try:
        message = await js.get_last_msg(scheduler_stream.name, job.schedule_subject)
    except NotFoundError:
        return {}
    stored = message.headers or {}
    return {
        key: value for key, value in stored.items() if key.startswith("Nats-Schedule")
    }
