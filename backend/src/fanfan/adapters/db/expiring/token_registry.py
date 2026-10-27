import hashlib
import hmac
from datetime import timedelta
from enum import StrEnum
from typing import override
from uuid import UUID

from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from fanfan.adapters.db.models import AuthCodeORM
from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.core.exceptions.rate_limit import TooManyAttempts, TooManyOtpAttempts
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig


class _Purpose(StrEnum):
    EMAIL_CONFIRMATION = "email-confirmation"
    EMAIL_LOGIN = "email-login"


class PostgresTokenRegistry(TokenRegistry):
    """One row per purpose and subject, so issuing a code replaces the last one."""

    def __init__(
        self, engine: AsyncEngine, config: WebConfig, rate_limiter: RateLimiter
    ) -> None:
        self.engine = engine
        self._secret = config.secret_key.get_secret_value().encode()
        self.rate_limiter = rate_limiter

    def _hash_code(self, code: str) -> str:
        return hmac.new(self._secret, code.encode(), hashlib.sha256).hexdigest()

    async def _issue(
        self, purpose: _Purpose, subject: str, code: str, value: str, ttl_seconds: int
    ) -> None:
        row = {
            "code_hash": self._hash_code(code),
            "value": value,
            "expires_at": func.now() + timedelta(seconds=max(1, ttl_seconds)),
        }
        statement = (
            insert(AuthCodeORM)
            .values(purpose=purpose, subject=subject, **row)
            .on_conflict_do_update(
                index_elements=[AuthCodeORM.purpose, AuthCodeORM.subject],
                set_=row,
            )
        )
        async with self.engine.begin() as connection:
            await connection.execute(statement)

    async def _consume(
        self,
        purpose: _Purpose,
        subject: str,
        code: str,
        max_attempts: int,
        window_seconds: int,
    ) -> str | None:
        attempts_key = f"{purpose}:attempts:{subject}"
        try:
            await self.rate_limiter.hit(
                attempts_key, limit=max_attempts, window_seconds=window_seconds
            )
        except TooManyAttempts as e:
            raise TooManyOtpAttempts(retry_after=e.details["retry_after"]) from e

        statement = (
            delete(AuthCodeORM)
            .where(
                AuthCodeORM.purpose == purpose,
                AuthCodeORM.subject == subject,
                AuthCodeORM.code_hash == self._hash_code(code),
                AuthCodeORM.expires_at > func.now(),
            )
            .returning(AuthCodeORM.value)
        )
        async with self.engine.begin() as connection:
            value = await connection.scalar(statement)
        if value is not None:
            await self.rate_limiter.reset(attempts_key)
        return value

    @override
    async def issue_email_confirmation_code(
        self,
        user_id: UserId,
        email: str,
        code: str,
        ttl_seconds: int,
    ) -> None:
        await self._issue(
            _Purpose.EMAIL_CONFIRMATION, str(user_id), code, email, ttl_seconds
        )

    @override
    async def consume_email_confirmation_code(
        self,
        user_id: UserId,
        code: str,
        max_attempts: int,
        window_seconds: int,
    ) -> str | None:
        return await self._consume(
            _Purpose.EMAIL_CONFIRMATION,
            str(user_id),
            code,
            max_attempts,
            window_seconds,
        )

    @override
    async def issue_email_login_code(
        self,
        user_id: UserId,
        email: str,
        code: str,
        ttl_seconds: int,
    ) -> None:
        await self._issue(_Purpose.EMAIL_LOGIN, email, code, str(user_id), ttl_seconds)

    @override
    async def consume_email_login_code(
        self,
        email: str,
        code: str,
        max_attempts: int,
        window_seconds: int,
    ) -> UserId | None:
        value = await self._consume(
            _Purpose.EMAIL_LOGIN, email, code, max_attempts, window_seconds
        )
        if value is None:
            return None
        return UserId(UUID(value))
