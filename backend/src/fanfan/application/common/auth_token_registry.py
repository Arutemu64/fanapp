from typing import Protocol


class AuthTokenRegistry(Protocol):
    async def consume_refresh_token_jti(
        self,
        jti: str,
        ttl_seconds: int,
    ) -> bool:
        """Mark refresh token as used once."""

    async def issue_email_verification_nonce(
        self,
        nonce: str,
        ttl_seconds: int,
    ) -> None:
        """Store an issued email verification nonce."""

    async def consume_email_verification_nonce(
        self,
        nonce: str,
        ttl_seconds: int,
    ) -> bool:
        """Consume nonce once."""
