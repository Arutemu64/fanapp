import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import sentry_sdk
from dishka import AsyncContainer

from fanfan.application.interactors.cosplay2.sync_cosplay2 import SyncCosplay2
from fanfan.application.interactors.outbox.purge_outbox_events import (
    PurgeOutboxEvents,
)
from fanfan.application.interactors.ticketscloud.sync_tcloud import SyncTCloud
from fanfan.presentation.scheduler.config import SchedulerConfig

logger = logging.getLogger(__name__)


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
        JobDefinition(
            id="outbox_retention",
            cron=config.outbox_retention_cron,
            interactor=PurgeOutboxEvents,
        ),
    ]


def make_interactor_job(
    container: AsyncContainer, interactor_type: type[Any]
) -> Callable[[], Awaitable[None]]:
    # Each run opens a fresh REQUEST scope and resolves the interactor,
    # mirroring the CLI commands (presentation/cli/commands).
    async def job() -> None:
        try:
            async with container() as request_container:
                interactor = await request_container.get(interactor_type)
                await interactor()
        except Exception:
            # Capture explicitly so background failures are always reported to
            # Sentry with context, instead of relying on APScheduler's logging
            # being picked up indirectly. Re-raise so APScheduler still records
            # the missed run.
            logger.exception("Scheduled job for '%s' failed", interactor_type.__name__)
            sentry_sdk.capture_exception()
            raise

    # APScheduler names jobs after the callable; without this they all log as
    # the opaque closure name "make_interactor_job.<locals>.job".
    job.__name__ = job.__qualname__ = interactor_type.__name__
    return job
