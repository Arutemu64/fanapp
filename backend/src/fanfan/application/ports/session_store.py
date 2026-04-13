from dataclasses import dataclass
from typing import Protocol

from fanfan.core.vo.user import UserId


@dataclass(frozen=True)
class SessionResolution:
    user_id: UserId | None
    touched: bool


class SessionStore(Protocol):
    async def create_session(self, user_id: UserId) -> str: ...

    async def resolve_session(self, session_id: str) -> SessionResolution: ...

    async def delete_session(self, session_id: str) -> None: ...

    async def revoke_user_sessions(self, user_id: UserId) -> None: ...
