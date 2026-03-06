import hashlib
import hmac

from redis.asyncio import Redis

from fanfan.application.common.auth_token_registry import AuthTokenRegistry
from fanfan.core.vo.user import UserId
from fanfan.presentation.web.config import WebConfig


class RedisAuthTokenRegistry(AuthTokenRegistry):
    def __init__(self, redis: Redis, config: WebConfig):
        self.redis = redis
        self._secret = config.secret_key.get_secret_value().encode()

    @staticmethod
    def _refresh_used_key(jti: str) -> str:
        return f"auth:refresh:used:{jti}"

    @staticmethod
    def _email_verification_key(token_hash: str) -> str:
        return f"auth:email-verification:{token_hash}"

    def _hash_token(self, token: str) -> str:
        digest = hmac.new(
            self._secret,
            token.encode(),
            hashlib.sha256,
        ).hexdigest()
        return digest

    async def consume_refresh_token_jti(self, jti: str, ttl_seconds: int) -> bool:
        ttl = max(1, ttl_seconds)
        result = await self.redis.set(
            name=self._refresh_used_key(jti),
            value="1",
            ex=ttl,
            nx=True,
        )
        return bool(result)

    async def issue_email_verification_token(
        self,
        token: str,
        user_id: UserId,
        ttl_seconds: int,
    ) -> None:
        ttl = max(1, ttl_seconds)
        await self.redis.set(
            name=self._email_verification_key(self._hash_token(token)),
            value=str(user_id),
            ex=ttl,
        )

    async def consume_email_verification_token(
        self,
        token: str,
    ) -> UserId | None:
        key = self._email_verification_key(self._hash_token(token))
        stored_user_id = await self.redis.getdel(key)

        if not stored_user_id:
            return None

        if isinstance(stored_user_id, bytes):
            stored_user_id = stored_user_id.decode()

        return UserId(stored_user_id)
