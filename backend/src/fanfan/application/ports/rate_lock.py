from types import TracebackType
from typing import Protocol


class RateLock(Protocol):
    """Distributed lock that also enforces a cooldown between successful runs.

    The lock does two jobs at once:
      - serializes callers, so only one runs the guarded block at a time;
      - makes the cooldown check atomic — without it, two concurrent callers
        could both read the old timestamp, both pass, and both proceed.

    The cooldown timestamp is written only on a clean exit, so a failed
    operation does not consume the cooldown and can be retried immediately.
    """

    async def __aenter__(self) -> None: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...


class RateLockFactory(Protocol):
    def __call__(
        self,
        limit_name: str,
        cooldown_period: float = 60,
        blocking: bool = True,
        lock_timeout: float = 60,
        blocking_timeout: float | None = None,
    ) -> RateLock: ...
