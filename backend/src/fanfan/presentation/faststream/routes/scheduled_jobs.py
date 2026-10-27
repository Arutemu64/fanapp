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
    @inject
    async def handler(
        container: FromDishka[AsyncContainer],
        msg: NatsMessage,
    ) -> None:
        interactor = await container.get(job.interactor)
        async with in_progress_heartbeat(msg):
            await interactor()

    handler.__name__ = handler.__qualname__ = f"run_{job.id}"
    scheduled_jobs_router.subscriber(
        job.tick_subject,
        stream=scheduler_stream,
        pull_sub=PullSub(),
        durable=f"scheduled_{job.id}",
        ack_policy=AckPolicy.NACK_ON_ERROR,
        config=consumer_config(),
    )(handler)


for _job in SCHEDULED_JOBS:
    _register(_job)
