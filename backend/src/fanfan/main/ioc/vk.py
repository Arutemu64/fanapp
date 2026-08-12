from collections.abc import AsyncIterable

import httpx2
from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.vk.client import VkApiClient
from fanfan.adapters.vk.config import VkConfig
from fanfan.adapters.vk.notifier import VkNotifier
from fanfan.application.ports.notifier import VkNotifierPort

# httpx2 defaults to a 5s deadline on every operation. VK messaging runs on the
# background notification consumer, not an interactive path, so give the read a
# generous budget while keeping connect short so an unreachable host fails fast.
VK_TIMEOUT = httpx2.Timeout(30.0, connect=10.0)


class VkProvider(Provider):
    scope = Scope.APP

    @provide
    def get_vk_config(self, config: EnvConfig) -> VkConfig:
        return config.vk

    @provide
    async def get_vk_api_client(self, config: VkConfig) -> AsyncIterable[VkApiClient]:
        # APP scope: one client (and its connection pool) is reused across every
        # send, so a notification burst reuses the TCP+TLS connection to VK
        # instead of re-handshaking per message. The wrapper type keeps a bare
        # httpx2.AsyncClient out of the container.
        async with httpx2.AsyncClient(timeout=VK_TIMEOUT) as client:
            yield VkApiClient(client=client, config=config)

    vk_notifier = provide(VkNotifier, scope=Scope.REQUEST, provides=VkNotifierPort)
