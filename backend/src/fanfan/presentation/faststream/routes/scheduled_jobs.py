from dishka import AsyncContainer, FromDishka
from dishka_faststream import inject
from faststream import AckPolicy
from faststream.nats import NatsMessage, NatsRouter, PullSub

from fanfan.presentation.faststream.jstream import scheduler_stream
from fanfan.presentation.faststream.redelivery import (
    consumer_config,
    in_progress_heartbeat,
)
from fanfan.presentation.faststream.schedules.jobs import SCHEDULED_JOBS, ScheduledJob

scheduled_jobs_router = NatsRouter()


def _register(job: ScheduledJob) -> None:
    # A durable per job rather than one on scheduler.tick.*: a pull subscriber
    # handles one message at a time, so a shared one would hold the nightly
    # purge behind an hour-long TicketsCloud sweep. Being durable is also what
    # keeps two worker replicas from both running one tick.
    @inject
    async def handler(
        container: FromDishka[AsyncContainer],
        msg: NatsMessage,
    ) -> None:
        interactor = await container.get(job.interactor)
        # A sync can outlast AckWait; see routes/sync.py.
        async with in_progress_heartbeat(msg):
            await interactor()

    # FastStream names the handler in logs and Sentry after the function.
    handler.__name__ = handler.__qualname__ = f"run_{job.id}"
    scheduled_jobs_router.subscriber(
        job.tick_subject,
        stream=scheduler_stream,
        pull_sub=PullSub(),
        durable=f"scheduled_{job.id}",
        # A failed run is retried on the usual backoff (redelivery.py) until
        # the next tick replaces its message: the stream keeps one per subject.
        ack_policy=AckPolicy.NACK_ON_ERROR,
        config=consumer_config(),
    )(handler)


for _job in SCHEDULED_JOBS:
    _register(_job)
