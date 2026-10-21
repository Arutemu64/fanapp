from collections.abc import AsyncIterable

from adaptix import Retort
from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from fanfan.adapters.redis.realtime_gateway import ValkeyRealtimeGateway
from fanfan.application.ports.realtime_gateway import RealtimeGateway


class RealtimeProvider(Provider):
    scope = Scope.APP

    @provide
    async def get_realtime_gateway(
        self, redis: Redis, retort: Retort
    ) -> AsyncIterable[RealtimeGateway]:
        gateway = ValkeyRealtimeGateway(redis, retort)
        yield gateway
        # Stop the pub/sub reader before the Redis client it reads from closes.
        await gateway.close()
