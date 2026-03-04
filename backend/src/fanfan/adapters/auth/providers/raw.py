from uuid import UUID

from fanfan.application.common.id_provider import IdProvider
from fanfan.core.vo.user import UserId


class RawIdProvider(IdProvider):
    async def get_current_user_id(self) -> UserId | None:
        return UserId(UUID("00000000-0000-0000-0000-000000000000"))
