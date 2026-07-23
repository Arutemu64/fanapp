import logging

from pydantic import BaseModel

from fanfan.application.interactors.cosplay.sync_cosplay import SyncCosplay
from fanfan.application.interactors.tickets.sync_tickets import SyncTickets
from fanfan.application.ports.rate_lock import RateLockFactory
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.rate_limit import RateLimitCooldown, RateLimitInUse
from fanfan.core.exceptions.sync import SyncAlreadyRunning, SyncTooFast
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.sync import SyncSource, SyncTrigger

logger = logging.getLogger(__name__)

# Cooldown between manual runs of the same source, so an org can't hammer the
# vendor APIs by re-pressing the button right after a run finishes.
MANUAL_SYNC_COOLDOWN_SECONDS = 60
# A full sync can take a while; the lock must outlive it or a second manual run
# could start while the first is still importing.
SYNC_LOCK_TIMEOUT_SECONDS = 600


class RunSyncInput(BaseModel):
    source: SyncSource


class RunSync:
    """Manually run an external sync (org tool).

    Wraps the same sync interactors the scheduler and CLI use, adding the
    permission gate and a per-source rate lock — the system-triggered paths
    stay unauthenticated on purpose.
    """

    def __init__(
        self,
        sync_cosplay: SyncCosplay,
        sync_tickets: SyncTickets,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        rate_lock_factory: RateLockFactory,
    ) -> None:
        self.sync_cosplay = sync_cosplay
        self.sync_tickets = sync_tickets
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.rate_lock_factory = rate_lock_factory

    async def __call__(self, data: RunSyncInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SYNC_RUN
        )

        lock = self.rate_lock_factory(
            f"sync:{data.source.value}",
            cooldown_period=MANUAL_SYNC_COOLDOWN_SECONDS,
            blocking=False,
            lock_timeout=SYNC_LOCK_TIMEOUT_SECONDS,
        )
        try:
            async with lock:
                logger.info(
                    "Manual sync started",
                    extra={
                        "source": data.source.value,
                        "actor_id": str(current_user.id),
                    },
                )
                if data.source is SyncSource.COSPLAY2:
                    await self.sync_cosplay(trigger=SyncTrigger.MANUAL)
                else:
                    await self.sync_tickets(trigger=SyncTrigger.MANUAL)
        except RateLimitInUse as e:
            raise SyncAlreadyRunning from e
        except RateLimitCooldown as e:
            raise SyncTooFast(retry_after=e.details["retry_after"]) from e
