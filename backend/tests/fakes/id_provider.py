from fanfan.application.ports.id_provider import IdProvider
from fanfan.core.vo.user import UserId


class FakeIdProvider(IdProvider):
    def __init__(self) -> None:
        self.user_id = None

    async def get_current_user_id(self) -> UserId | None:
        return self.user_id

    def set_current_user_id(self, user_id: UserId | None) -> None:
        self.user_id = user_id
