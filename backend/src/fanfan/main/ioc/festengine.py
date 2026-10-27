from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.presentation.web.festengine import FestEngineConfig


class FestEngineProvider(Provider):
    scope = Scope.APP

    @provide
    def get_festengine_config(self, config: EnvConfig) -> FestEngineConfig:
        return config.festengine
