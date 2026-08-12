from collections.abc import AsyncIterable

import httpx2
from adaptix import Retort
from dishka import Provider, Scope, provide

from fanfan.adapters.api.base import DEFAULT_TIMEOUT
from fanfan.adapters.api.ticketscloud.client import TCloudClient
from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.api.ticketscloud.exceptions import NoTCloudConfigProvided
from fanfan.adapters.api.ticketscloud.source import TCloudSource
from fanfan.adapters.config.models import EnvConfig
from fanfan.application.ports.sources.tickets import TicketsSource


class TCloudProvider(Provider):
    scope = Scope.REQUEST

    tcloud_source = provide(TCloudSource, provides=TicketsSource)

    @provide(scope=Scope.APP)
    def get_tcloud_config(self, config: EnvConfig) -> TCloudConfig:
        if config.tcloud is None:
            raise NoTCloudConfigProvided
        return config.tcloud

    # APP scope: one client (and its connection pool) is reused across every
    # sync, so the paginated sweep and successive runs reuse the connection to
    # the vendor instead of re-handshaking. The request-scoped source depends on
    # it; the wrapper type keeps a bare httpx2.AsyncClient out of the container.
    @provide(scope=Scope.APP)
    async def get_tcloud_client(
        self, config: TCloudConfig, retort: Retort
    ) -> AsyncIterable[TCloudClient]:
        headers = {"Authorization": f"key {config.api_key.get_secret_value()}"}
        async with httpx2.AsyncClient(
            base_url="https://ticketscloud.com/v2/",
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        ) as client:
            yield TCloudClient(client=client, retort=retort)
