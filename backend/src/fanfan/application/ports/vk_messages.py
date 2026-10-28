from typing import Protocol


class VkMessagesPermission(Protocol):
    async def is_allowed(self, vk_user_id: int) -> bool:
        """Whether the VK community may message this VK user right now."""
        ...
