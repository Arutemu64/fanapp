from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.redis.auth_token_registry import RedisTokenRegistry
from fanfan.adapters.redis.config import RedisConfig
from fanfan.adapters.redis.factory import create_redis
from fanfan.adapters.redis.rate_lock import RedisRateLockFactory
from fanfan.adapters.redis.utils import RedisRetort, get_redis_retort
from fanfan.application.ports.rate_lock import RateLockFactory
from fanfan.application.ports.token_registry import TokenRegistry


class RedisProvider(Provider):
    scope = Scope.APP

    @provide
    def get_redis_config(self, config: EnvConfig) -> RedisConfig:
        return config.redis

    @provide
    async def get_redis(self, config: RedisConfig) -> AsyncIterable[Redis]:
        async with create_redis(config) as redis:
            yield redis

    @provide
    def get_redis_retort(self) -> RedisRetort:
        return get_redis_retort()

    auth_token_registry = provide(
        RedisTokenRegistry,
        provides=TokenRegistry,
        scope=Scope.APP,
    )
    rate_limit_factory = provide(
        RedisRateLockFactory,
        provides=RateLockFactory,
        scope=Scope.APP,
    )
