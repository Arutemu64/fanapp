from collections.abc import AsyncIterable

import httpx2
from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.vk.config import VkConfig
from fanfan.adapters.vk.notifier import VkNotifier
from fanfan.application.ports.notifier import VkNotifierPort

# VK messaging runs on the background notification consumer, so a generous but
# bounded budget: a slow VK must not wedge the worker. connect stays short so an
# unreachable host fails fast instead of hanging the whole send.
VK_TIMEOUT = httpx2.Timeout(30.0, connect=10.0)


class VkProvider(Provider):
    scope = Scope.APP

    @provide
    def get_vk_config(self, config: EnvConfig) -> VkConfig:
        return config.vk

    @provide
    async def get_vk_client(self) -> AsyncIterable[httpx2.AsyncClient]:
        async with httpx2.AsyncClient(timeout=VK_TIMEOUT) as client:
            yield client

    vk_notifier = provide(VkNotifier, scope=Scope.REQUEST, provides=VkNotifierPort)
