from abc import abstractmethod
from typing import Protocol

from fanfan.core.vo.user import UserId


class IdProvider(Protocol):
    @abstractmethod
    async def get_current_user_id(self) -> UserId | None:
        raise NotImplementedError
