from typing import Protocol

from fanfan.core.vo.user import UserId


class TokenRegistry(Protocol):
    async def issue_email_confirmation_code(
        self,
        user_id: UserId,
        email: str,
        code: str,
        ttl_seconds: int,
    ) -> None: ...

    async def consume_email_confirmation_code(
        self,
        user_id: UserId,
        code: str,
    ) -> str | None: ...

    async def issue_email_login_code(
        self,
        user_id: UserId,
        email: str,
        code: str,
        ttl_seconds: int,
    ) -> None: ...

    async def consume_email_login_code(
        self,
        email: str,
        code: str,
    ) -> UserId | None: ...
