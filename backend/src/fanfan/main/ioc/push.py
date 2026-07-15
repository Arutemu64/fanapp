from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.push.config import PushConfig
from fanfan.adapters.push.push import PushNotifier
from fanfan.application.ports.notifier import PushNotifierPort


class PushProvider(Provider):
    scope = Scope.APP

    @provide
    def get_push_config(self, config: EnvConfig) -> PushConfig:
        return config.push

    push_notifier = provide(
        PushNotifier, scope=Scope.REQUEST, provides=PushNotifierPort
    )
