from collections.abc import AsyncIterable

import httpx2
from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.push.client import WebPushClient
from fanfan.adapters.push.config import PushConfig
from fanfan.adapters.push.push import PushNotifier
from fanfan.application.ports.notifier import PushNotifierPort

# httpx2 defaults to a 5s deadline on every operation; make it explicit. Push
# services should answer quickly, so keep the budget tight — a stalled endpoint
# must not wedge the notification consumer.
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
        # APP scope: one client (and its connection pool) reused across every
        # push. Endpoints span many hosts, but httpx pools per host, so bursts to
        # the same push service reuse connections. The wrapper type keeps a bare
        # httpx2.AsyncClient out of the container.
        async with httpx2.AsyncClient(timeout=WEBPUSH_TIMEOUT) as client:
            yield WebPushClient(client=client, config=config)

    push_notifier = provide(
        PushNotifier, scope=Scope.REQUEST, provides=PushNotifierPort
    )
