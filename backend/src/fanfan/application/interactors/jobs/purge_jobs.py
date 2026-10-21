import logging

from fanfan.application.interactors.jobs.config import JobsConfig
from fanfan.application.ports.gateways.jobs import JobGateway
from fanfan.application.ports.uow import UnitOfWork

logger = logging.getLogger(__name__)


class PurgeJobs:
    """Retention job: drop finished jobs older than the configured age."""

    def __init__(
        self,
        job_gateway: JobGateway,
        uow: UnitOfWork,
        config: JobsConfig,
    ) -> None:
        self.job_gateway = job_gateway
        self.uow = uow
        self.config = config

    async def __call__(self) -> None:
        deleted = await self.job_gateway.delete_finished_before(
            self.config.retention_days
        )
        await self.uow.commit()
        logger.info("Job retention purged finished jobs", extra={"job_count": deleted})
