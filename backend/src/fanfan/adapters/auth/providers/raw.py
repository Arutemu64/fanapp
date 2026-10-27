from typing import override

from fanfan.application.ports.id_provider import IdProvider
from fanfan.core.vo.user import SYSTEM_USER_ID, UserId


class RawIdProvider(IdProvider):
    @override
    async def get_current_user_id(self) -> UserId | None:
        return SYSTEM_USER_ID
