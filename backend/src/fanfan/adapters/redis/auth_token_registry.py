import hashlib
import hmac
import json

from redis.asyncio import Redis

from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig


class RedisTokenRegistry(TokenRegistry):
    def __init__(self, redis: Redis, config: WebConfig):
        self.redis = redis
        self._secret = config.secret_key.get_secret_value().encode()

    @staticmethod
    def _refresh_used_key(jti: str) -> str:
        return f"auth:refresh:used:{jti}"

    @staticmethod
    def _email_confirmation_code_key(user_id: UserId, code_hash: str) -> str:
        return f"auth:email-confirmation:{user_id}:{code_hash}"

    @staticmethod
    def _email_login_code_key(email: str, code_hash: str) -> str:
        return f"auth:email-login-code:{email}:{code_hash}"

    def _hash_code(self, code: str) -> str:
        return hmac.new(
            self._secret,
            code.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def consume_refresh_token_jti(self, jti: str, ttl_seconds: int) -> bool:
        ttl = max(1, ttl_seconds)
        result = await self.redis.set(
            name=self._refresh_used_key(jti),
            value="1",
            ex=ttl,
            nx=True,  # Only set if not already used
        )
        return bool(result)

    async def revoke_refresh_token_jti(self, jti: str, ttl_seconds: int) -> None:
        ttl = max(1, ttl_seconds)
        await self.redis.set(
            name=self._refresh_used_key(jti),
            value="1",
            ex=ttl,
        )

    async def issue_email_confirmation_code(
        self,
        user_id: UserId,
        email: str,
        code: str,
        ttl_seconds: int,
    ) -> None:
        ttl = max(1, ttl_seconds)
        payload = json.dumps({"email": email})
        await self.redis.set(
            name=self._email_confirmation_code_key(user_id, self._hash_code(code)),
            value=payload,
            ex=ttl,
        )

    async def consume_email_confirmation_code(
        self,
        user_id: UserId,
        code: str,
    ) -> str | None:
        key = self._email_confirmation_code_key(user_id, self._hash_code(code))
        stored_payload = await self.redis.getdel(key)

        if not stored_payload:
            return None

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
        payload = json.dumps({"user_id": str(user_id)})
        await self.redis.set(
            name=self._email_login_code_key(email, self._hash_code(code)),
            value=payload,
            ex=ttl,
        )

    async def consume_email_login_code(
        self,
        email: str,
        code: str,
    ) -> UserId | None:
        key = self._email_login_code_key(email, self._hash_code(code))
        stored_payload = await self.redis.getdel(key)

        if not stored_payload:
            return None

        if isinstance(stored_payload, bytes):
            stored_payload = stored_payload.decode()

        payload = json.loads(stored_payload)
        return UserId(payload["user_id"])
