from typing import Protocol

from fanfan.core.vo.user import UserId


class AuthTokenRegistry(Protocol):
    async def consume_refresh_token_jti(
        self,
        jti: str,
        ttl_seconds: int,
    ) -> bool:
        """Mark refresh token as used once."""

    async def issue_email_verification_token(
        self,
        token: str,
        user_id: UserId,
        ttl_seconds: int,
    ) -> None:
        """Store an issued email verification token."""

    async def consume_email_verification_token(
        self,
        token: str,
    ) -> UserId | None:
        """Consume token once and return its user id when valid."""
