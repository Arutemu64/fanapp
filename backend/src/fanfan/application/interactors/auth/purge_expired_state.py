import logging

from fanfan.application.ports.expired_state import ExpiredStatePurger

logger = logging.getLogger(__name__)


class PurgeExpiredState:
    """Retention job: drop expired sessions, email codes, rate limits and
    cooldowns.
    """

    def __init__(self, purger: ExpiredStatePurger) -> None:
        self.purger = purger

    async def __call__(self) -> None:
        deleted = await self.purger.purge_expired()
        logger.info("Purged expired auth state", extra={"row_count": deleted})
