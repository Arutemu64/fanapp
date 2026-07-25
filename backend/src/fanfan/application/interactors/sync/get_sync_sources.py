from typing import NewType

from fanfan.application.dto.sync import SyncSourceStatusDTO
from fanfan.application.ports.gateways.sync_runs import SyncRunGateway
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.sync import SyncSource

# Which vendors this deployment has credentials for. Both integrations are
# independently optional, so the set is computed once in the composition root
# (main/ioc/sync.py) from EnvConfig and injected as a plain value: the vendor
# config models live in adapters/, which the application layer may not import.
AvailableSyncSources = NewType("AvailableSyncSources", frozenset[SyncSource])


class GetSyncSources:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
        sync_run_gateway: SyncRunGateway,
        available_sources: AvailableSyncSources,
    ):
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service
        self.sync_run_gateway = sync_run_gateway
        self.available_sources = available_sources

    async def __call__(self) -> list[SyncSourceStatusDTO]:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SYNC_RUN
        )

        latest = await self.sync_run_gateway.read_latest_by_source()
        return [
            SyncSourceStatusDTO(
                source=source,
                available=source in self.available_sources,
                last_run=latest.get(source),
            )
            for source in SyncSource
        ]
