from collections.abc import AsyncIterable

import httpx2
from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.vk.client import VkApiClient
from fanfan.adapters.vk.config import VkConfig
from fanfan.adapters.vk.messages_permission import VkApiMessagesPermission
from fanfan.adapters.vk.notifier import VkNotifier
from fanfan.application.ports.notifier import VkNotifierPort
from fanfan.application.ports.vk_messages import VkMessagesPermission

VK_TIMEOUT = httpx2.Timeout(30.0, connect=10.0)


class VkProvider(Provider):
    scope = Scope.APP

    @provide
    def get_vk_config(self, config: EnvConfig) -> VkConfig:
        return config.vk

    @provide
    async def get_vk_api_client(self, config: VkConfig) -> AsyncIterable[VkApiClient]:
        async with httpx2.AsyncClient(timeout=VK_TIMEOUT) as client:
            yield VkApiClient(client=client, config=config)

    vk_notifier = provide(VkNotifier, scope=Scope.REQUEST, provides=VkNotifierPort)
    vk_messages_permission = provide(
        VkApiMessagesPermission, provides=VkMessagesPermission
    )
