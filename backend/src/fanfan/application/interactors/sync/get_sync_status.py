from fanfan.application.dto.sync import SyncSourceStatusDTO, SyncStatusDTO
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.sync import SyncSource

RECENT_RUNS_LIMIT = 10


class GetSyncStatus:
    def __init__(
        self,
        sync_run_gateway: SyncRunGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ) -> None:
        self.sync_run_gateway = sync_run_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def __call__(self) -> SyncStatusDTO:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SYNC_RUN
        )

        sources = [
            SyncSourceStatusDTO(
                source=source,
                last_success_at=await self.sync_run_gateway.read_last_completed_at(
                    source
                ),
                recent_runs=await self.sync_run_gateway.read_recent_runs(
                    source, limit=RECENT_RUNS_LIMIT
                ),
            )
            for source in SyncSource
        ]
        return SyncStatusDTO(sources=sources)
