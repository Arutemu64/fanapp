from collections.abc import AsyncIterable

from cosplay2py import AsyncCosplay2
from dishka import Provider, Scope, provide

from fanfan.adapters.api.base import DEFAULT_TIMEOUT
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

    @provide(scope=Scope.APP)
    async def get_cosplay2_client(
        self, config: Cosplay2Config
    ) -> AsyncIterable[AsyncCosplay2]:
        async with AsyncCosplay2(
            base_url=config.build_api_base_url(),
            api_key=config.api_key,
            api_secret=config.api_secret.get_secret_value(),
            timeout=DEFAULT_TIMEOUT,
        ) as client:
            yield client
