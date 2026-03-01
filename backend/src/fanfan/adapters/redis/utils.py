from typing import NewType

from adaptix import Retort, dumper, loader

# Retort optimized for Redis usage
RedisRetort = NewType("RedisRetort", Retort)


def get_redis_retort() -> RedisRetort:
    retort = Retort(
        strict_coercion=False,
        recipe=[
            dumper(bool, int),  # Dumping bool to Redis
            loader(bool, lambda x: bool(int(x))),  # Loading bool from Redis
        ],
    )
    return RedisRetort(retort)
