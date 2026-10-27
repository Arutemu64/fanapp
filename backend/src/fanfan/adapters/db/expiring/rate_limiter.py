import math
from datetime import timedelta
from typing import override

from sqlalchemy import case, delete, func
from sqlalchemy.dialects.postgresql import insert

from fanfan.adapters.db.expiring.transactions import TransactionSource
from fanfan.adapters.db.models import RateLimitORM
from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.core.exceptions.rate_limit import TooManyAttempts


class PostgresRateLimiter(RateLimiter):
    """Fixed-window attempt counter, one upsert per hit.

    Runs in its own transaction, so a hit sticks even when the caller's unit of
    work rolls back (a wrong password raises after counting).
    """

    def __init__(self, transactions: TransactionSource) -> None:
        self.transactions = transactions

    @override
    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
        window_end = func.now() + timedelta(seconds=max(1, window_seconds))
        window_over = RateLimitORM.expires_at <= func.now()
        statement = (
            insert(RateLimitORM)
            .values(key=key, hits=1, expires_at=window_end)
            .on_conflict_do_update(
                index_elements=[RateLimitORM.key],
                set_={
                    "hits": case((window_over, 1), else_=RateLimitORM.hits + 1),
                    "expires_at": case(
                        (window_over, window_end), else_=RateLimitORM.expires_at
                    ),
                },
            )
            .returning(
                RateLimitORM.hits,
                func.extract("epoch", RateLimitORM.expires_at - func.now()),
            )
        )
        async with self.transactions.begin() as connection:
            hits, seconds_left = (await connection.execute(statement)).one()
        if hits > limit:
            raise TooManyAttempts(retry_after=max(1, math.ceil(seconds_left)))

    @override
    async def reset(self, key: str) -> None:
        async with self.transactions.begin() as connection:
            await connection.execute(
                delete(RateLimitORM).where(RateLimitORM.key == key)
            )
