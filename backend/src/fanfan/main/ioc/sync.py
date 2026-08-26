from dishka import Provider, Scope, provide, provide_all

from fanfan.adapters.config.models import EnvConfig
from fanfan.application.interactors.sync.execute_cosplay_sync import ExecuteCosplaySync
from fanfan.application.interactors.sync.execute_tickets_sync import ExecuteTicketsSync
from fanfan.application.interactors.sync.get_sync_sources import (
    AvailableSyncSources,
    GetSyncSources,
)
from fanfan.application.interactors.sync.request_sync import RequestSync
from fanfan.core.vo.sync import SyncSource


class SyncProvider(Provider):
    scope = Scope.REQUEST

    request_sync = provide(RequestSync)
    get_sync_sources = provide(GetSyncSources)

    # One interactor per vendor rather than one that dispatches on source:
    # resolving either would otherwise pull in *both* vendor configs, and each
    # raises when its vendor is unset — breaking single-vendor deployments.
    execute_syncs = provide_all(ExecuteCosplaySync, ExecuteTicketsSync)

    @provide(scope=Scope.APP)
    def get_available_sync_sources(self, config: EnvConfig) -> AvailableSyncSources:
        """Which vendors this deployment is configured for.

        Read here, in the composition root, because the vendor config models live
        in adapters/ and the application layer may not import them.
        """
        available = set()
        if config.cosplay2 is not None:
            available.add(SyncSource.COSPLAY2)
        if config.tcloud is not None:
            available.add(SyncSource.TCLOUD)
        return AvailableSyncSources(frozenset(available))
