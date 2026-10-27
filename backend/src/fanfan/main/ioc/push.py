from collections.abc import AsyncIterable

import httpx2
from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.push.client import WebPushClient
from fanfan.adapters.push.config import PushConfig
from fanfan.adapters.push.push import PushNotifier
from fanfan.application.ports.notifier import PushNotifierPort

WEBPUSH_TIMEOUT = httpx2.Timeout(10.0, connect=5.0)


class PushProvider(Provider):
    scope = Scope.APP

    @provide
    def get_push_config(self, config: EnvConfig) -> PushConfig:
        return config.push

    @provide
    async def get_web_push_client(
        self, config: PushConfig
    ) -> AsyncIterable[WebPushClient]:
        async with httpx2.AsyncClient(timeout=WEBPUSH_TIMEOUT) as client:
            yield WebPushClient(client=client, config=config)

    push_notifier = provide(
        PushNotifier, scope=Scope.REQUEST, provides=PushNotifierPort
    )
