from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from dishka import AsyncContainer

from fanfan.application.interactors.cosplay2.sync_cosplay2 import SyncCosplay2
from fanfan.application.interactors.ticketscloud.sync_tcloud import SyncTCloud
from fanfan.presentation.scheduler.config import SchedulerConfig


@dataclass(frozen=True, slots=True)
class JobDefinition:
    id: str
    cron: str | None
    interactor: type[Any]


def get_job_definitions(config: SchedulerConfig) -> list[JobDefinition]:
    return [
        JobDefinition(
            id="sync_tcloud",
            cron=config.sync_tcloud_cron,
            interactor=SyncTCloud,
        ),
        JobDefinition(
            id="sync_cosplay2",
            cron=config.sync_cosplay2_cron,
            interactor=SyncCosplay2,
        ),
    ]


def make_interactor_job(
    container: AsyncContainer, interactor_type: type[Any]
) -> Callable[[], Awaitable[None]]:
    # Each run opens a fresh REQUEST scope and resolves the interactor,
    # mirroring the CLI commands (presentation/cli/commands).
    async def job() -> None:
        async with container() as request_container:
            interactor = await request_container.get(interactor_type)
            await interactor()

    return job
