from typing import override

from fanfan.adapters.vk.client import VkApiClient
from fanfan.application.ports.vk_messages import VkMessagesPermission


class VkApiMessagesPermission(VkMessagesPermission):
    def __init__(self, client: VkApiClient) -> None:
        self.client = client

    @override
    async def is_allowed(self, vk_user_id: int) -> bool:
        return await self.client.is_messages_from_group_allowed(user_id=vk_user_id)
