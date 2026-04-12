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

    async def issue_email_verification_token(
        self,
        token: str,
        user_id: UserId,
        email: str,
        ttl_seconds: int,
    ) -> None: ...

    async def consume_email_verification_token(
        self,
        token: str,
    ) -> tuple[UserId, str] | None: ...

    async def issue_email_login_token(
        self,
        token: str,
        user_id: UserId,
        email: str,
        ttl_seconds: int,
    ) -> None: ...

    async def consume_email_login_token(
        self,
        token: str,
    ) -> tuple[UserId, str] | None: ...
