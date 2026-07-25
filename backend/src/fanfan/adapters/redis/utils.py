from typing import NewType

from adaptix import Retort, dumper, loader

RedisRetort = NewType("RedisRetort", Retort)


def get_redis_retort() -> RedisRetort:
    retort = Retort(
        strict_coercion=False,
        recipe=[
            dumper(bool, int),
            loader(bool, lambda x: bool(int(x))),
        ],
    )
    return RedisRetort(retort)
