from redis.asyncio import Redis

from fanfan.application.common.auth_token_registry import AuthTokenRegistry


class RedisAuthTokenRegistry(AuthTokenRegistry):
    def __init__(self, redis: Redis):
        self.redis = redis

    @staticmethod
    def _refresh_used_key(jti: str) -> str:
        return f"auth:refresh:used:{jti}"

    @staticmethod
    def _email_issued_key(nonce: str) -> str:
        return f"auth:email-verification:issued:{nonce}"

    @staticmethod
    def _email_used_key(nonce: str) -> str:
        return f"auth:email-verification:used:{nonce}"

    async def consume_refresh_token_jti(self, jti: str, ttl_seconds: int) -> bool:
        ttl = max(1, ttl_seconds)
        result = await self.redis.set(
            name=self._refresh_used_key(jti),
            value="1",
            ex=ttl,
            nx=True,
        )
        return bool(result)

    async def issue_email_verification_nonce(
        self,
        nonce: str,
        ttl_seconds: int,
    ) -> None:
        ttl = max(1, ttl_seconds)
        await self.redis.set(
            name=self._email_issued_key(nonce),
            value="1",
            ex=ttl,
        )

    async def consume_email_verification_nonce(
        self,
        nonce: str,
        ttl_seconds: int,
    ) -> bool:
        issued_key = self._email_issued_key(nonce)
        used_key = self._email_used_key(nonce)
        ttl = max(1, ttl_seconds)

        async with self.redis.pipeline(transaction=True) as pipe:
            await pipe.get(issued_key)
            await pipe.set(name=used_key, value="1", ex=ttl, nx=True)
            issued, used_set = await pipe.execute()

        if not issued:
            return False
        return bool(used_set)
