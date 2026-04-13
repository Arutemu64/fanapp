from typing import Protocol

from fanfan.core.vo.user import UserId


class TokenRegistry(Protocol):
    async def consume_refresh_token_jti(self, jti: str, ttl_seconds: int) -> bool:
        """Mark a refresh token JTI as used.

        Returns True if it was fresh (first use).
        """
        ...

    async def revoke_refresh_token_jti(self, jti: str, ttl_seconds: int) -> None:
        """Forcibly mark a refresh token as used.

        This is used on logout so a stolen cookie cannot be replayed later.
        """
        ...

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
