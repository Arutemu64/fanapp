import hashlib
import hmac
import json

from redis.asyncio import Redis

from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig


class RedisAuthTokenRegistry:
    def __init__(self, redis: Redis, config: WebConfig):
        self.redis = redis
        self._secret = config.secret_key.get_secret_value().encode()

    @staticmethod
    def _refresh_used_key(jti: str) -> str:
        return f"auth:refresh:used:{jti}"

    @staticmethod
    def _email_verification_key(token_hash: str) -> str:
        return f"auth:email-verification:{token_hash}"

    @staticmethod
    def _email_login_key(token_hash: str) -> str:
        return f"auth:email-login:{token_hash}"

    def _hash_token(self, token: str) -> str:
        return hmac.new(
            self._secret,
            token.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def consume_refresh_token_jti(self, jti: str, ttl_seconds: int) -> bool:
        """Mark a refresh token JTI as used.

        Returns True if it was fresh (first use).
        """
        ttl = max(1, ttl_seconds)
        result = await self.redis.set(
            name=self._refresh_used_key(jti),
            value="1",
            ex=ttl,
            nx=True,  # Only set if not already used
        )
        return bool(result)

    async def revoke_refresh_token_jti(self, jti: str, ttl_seconds: int) -> None:
        """Forcibly mark a refresh token as used.

        This is used on logout so a stolen cookie cannot be replayed later.
        """
        ttl = max(1, ttl_seconds)
        await self.redis.set(
            name=self._refresh_used_key(jti),
            value="1",
            ex=ttl,
        )

    async def issue_email_verification_token(
        self,
        token: str,
        user_id: UserId,
        email: str,
        ttl_seconds: int,
    ) -> None:
        ttl = max(1, ttl_seconds)
        payload = json.dumps({"user_id": str(user_id), "email": email})
        await self.redis.set(
            name=self._email_verification_key(self._hash_token(token)),
            value=payload,
            ex=ttl,
        )

    async def consume_email_verification_token(
        self,
        token: str,
    ) -> tuple[UserId, str] | None:
        key = self._email_verification_key(self._hash_token(token))
        stored_payload = await self.redis.getdel(key)

        if not stored_payload:
            return None

        if isinstance(stored_payload, bytes):
            stored_payload = stored_payload.decode()

        payload = json.loads(stored_payload)
        return UserId(payload["user_id"]), payload["email"]

    async def issue_email_login_token(
        self,
        token: str,
        user_id: UserId,
        email: str,
        ttl_seconds: int,
    ) -> None:
        ttl = max(1, ttl_seconds)
        payload = json.dumps({"user_id": str(user_id), "email": email})
        await self.redis.set(
            name=self._email_login_key(self._hash_token(token)),
            value=payload,
            ex=ttl,
        )

    async def consume_email_login_token(
        self,
        token: str,
    ) -> tuple[UserId, str] | None:
        key = self._email_login_key(self._hash_token(token))
        stored_payload = await self.redis.getdel(key)

        if not stored_payload:
            return None

        if isinstance(stored_payload, bytes):
            stored_payload = stored_payload.decode()

        payload = json.loads(stored_payload)
        return UserId(payload["user_id"]), payload["email"]
