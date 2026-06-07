import hashlib
import hmac
import json
from collections.abc import Awaitable, Callable
from typing import cast
from uuid import UUID

from redis.asyncio import Redis

from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.core.exceptions.rate_limit import TooManyOtpAttempts
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig


class RedisTokenRegistry(TokenRegistry):
    def __init__(self, redis: Redis, config: WebConfig):
        self.redis = redis
        self._secret = config.secret_key.get_secret_value().encode()

    @staticmethod
    def _email_confirmation_code_key(user_id: UserId, code_hash: str) -> str:
        return f"auth:email-confirmation:{user_id}:{code_hash}"

    @staticmethod
    def _email_login_code_key(email: str, code_hash: str) -> str:
        return f"auth:email-login-code:{email}:{code_hash}"

    @staticmethod
    def _email_confirmation_active_key(user_id: UserId) -> str:
        # Points to the hash of the only code that should currently be valid
        # for this user, so issuing a new code can revoke the previous one.
        return f"auth:email-confirmation:active:{user_id}"

    @staticmethod
    def _email_login_active_key(email: str) -> str:
        return f"auth:email-login-code:active:{email}"

    @staticmethod
    def _email_confirmation_attempts_key(user_id: UserId) -> str:
        return f"auth:email-confirmation:attempts:{user_id}"

    @staticmethod
    def _email_login_attempts_key(email: str) -> str:
        return f"auth:email-login-code:attempts:{email}"

    def _hash_code(self, code: str) -> str:
        return hmac.new(
            self._secret,
            code.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def _register_attempt(
        self,
        attempts_key: str,
        max_attempts: int,
        window_seconds: int,
    ) -> None:
        # Count every consume attempt (including wrong guesses) and lock the
        # target once it goes over the limit. A wrong guess never deletes the
        # code, so without this counter brute-forcing a 6-digit code is free.
        # redis-py's async stubs mistype incr() as a plain int, so cast the
        # call to its real awaitable return type before awaiting it.
        attempts = await cast("Awaitable[int]", self.redis.incr(attempts_key))
        if attempts == 1:
            await self.redis.expire(attempts_key, max(1, window_seconds))
        if attempts > max_attempts:
            retry_after = await self.redis.ttl(attempts_key)
            raise TooManyOtpAttempts(retry_after=max(1, retry_after))

    async def _revoke_active_code(
        self,
        active_key: str,
        build_code_key: Callable[[str], str],
        ttl: int,
        new_code_hash: str,
    ) -> None:
        # Delete the previously issued code (if any) so only the newest code
        # stays valid, then remember the new code as the active one. Requests
        # are rate-limited per target, so this read-modify-write is not racy.
        old_hash = await self.redis.get(active_key)
        if old_hash:
            if isinstance(old_hash, bytes):
                old_hash = old_hash.decode()
            await self.redis.delete(build_code_key(old_hash))
        await self.redis.set(active_key, new_code_hash, ex=ttl)

    async def issue_email_confirmation_code(
        self,
        user_id: UserId,
        email: str,
        code: str,
        ttl_seconds: int,
    ) -> None:
        ttl = max(1, ttl_seconds)
        code_hash = self._hash_code(code)
        payload = json.dumps({"email": email})
        await self.redis.set(
            name=self._email_confirmation_code_key(user_id, code_hash),
            value=payload,
            ex=ttl,
        )
        await self._revoke_active_code(
            active_key=self._email_confirmation_active_key(user_id),
            build_code_key=lambda h: self._email_confirmation_code_key(user_id, h),
            ttl=ttl,
            new_code_hash=code_hash,
        )

    async def consume_email_confirmation_code(
        self,
        user_id: UserId,
        code: str,
        max_attempts: int,
        window_seconds: int,
    ) -> str | None:
        attempts_key = self._email_confirmation_attempts_key(user_id)
        await self._register_attempt(attempts_key, max_attempts, window_seconds)

        key = self._email_confirmation_code_key(user_id, self._hash_code(code))
        stored_payload = await self.redis.getdel(key)

        if not stored_payload:
            return None

        # Correct code: clear the attempt counter and the active-code pointer.
        await self.redis.delete(
            attempts_key,
            self._email_confirmation_active_key(user_id),
        )

        if isinstance(stored_payload, bytes):
            stored_payload = stored_payload.decode()

        payload = json.loads(stored_payload)
        return str(payload["email"])

    async def issue_email_login_code(
        self,
        user_id: UserId,
        email: str,
        code: str,
        ttl_seconds: int,
    ) -> None:
        ttl = max(1, ttl_seconds)
        code_hash = self._hash_code(code)
        payload = json.dumps({"user_id": str(user_id)})
        await self.redis.set(
            name=self._email_login_code_key(email, code_hash),
            value=payload,
            ex=ttl,
        )
        await self._revoke_active_code(
            active_key=self._email_login_active_key(email),
            build_code_key=lambda h: self._email_login_code_key(email, h),
            ttl=ttl,
            new_code_hash=code_hash,
        )

    async def consume_email_login_code(
        self,
        email: str,
        code: str,
        max_attempts: int,
        window_seconds: int,
    ) -> UserId | None:
        attempts_key = self._email_login_attempts_key(email)
        await self._register_attempt(attempts_key, max_attempts, window_seconds)

        key = self._email_login_code_key(email, self._hash_code(code))
        stored_payload = await self.redis.getdel(key)

        if not stored_payload:
            return None

        # Correct code: clear the attempt counter and the active-code pointer.
        await self.redis.delete(attempts_key, self._email_login_active_key(email))

        if isinstance(stored_payload, bytes):
            stored_payload = stored_payload.decode()

        payload = json.loads(stored_payload)
        return UserId(UUID(payload["user_id"]))
