from collections.abc import AsyncIterable

import httpx2
from adaptix import Retort
from dishka import Provider, Scope, provide

from fanfan.adapters.api.base import DEFAULT_TIMEOUT
from fanfan.adapters.api.cosplay2.client import Cosplay2Client
from fanfan.adapters.api.cosplay2.config import Cosplay2Config
from fanfan.adapters.api.cosplay2.exceptions import NoCosplay2ConfigProvided
from fanfan.adapters.api.cosplay2.source import Cosplay2Source
from fanfan.adapters.config.models import EnvConfig
from fanfan.application.ports.sources.cosplay import CosplaySource


class Cosplay2Provider(Provider):
    scope = Scope.REQUEST

    cosplay2_source = provide(Cosplay2Source, provides=CosplaySource)

    @provide(scope=Scope.APP)
    def get_cosplay2_config(self, config: EnvConfig) -> Cosplay2Config:
        if config.cosplay2 is None:
            raise NoCosplay2ConfigProvided
        return config.cosplay2

    # APP scope: one client (and its connection pool) is reused across every
    # sync, so the paginated sweep and successive runs reuse the connection to
    # the vendor instead of re-handshaking. The request-scoped source depends on
    # it; the wrapper type keeps a bare httpx2.AsyncClient out of the container.
    @provide(scope=Scope.APP)
    async def get_cosplay2_client(
        self, config: Cosplay2Config, retort: Retort
    ) -> AsyncIterable[Cosplay2Client]:
        headers = {
            "X-API-Key": config.api_key,
            "X-API-Secret": config.api_secret.get_secret_value(),
        }
        async with httpx2.AsyncClient(
            base_url=config.build_api_base_url(),
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        ) as client:
            yield Cosplay2Client(client=client, retort=retort)
