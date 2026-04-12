from abc import abstractmethod
from types import TracebackType
from typing import Protocol


class RateLock(Protocol):
    @abstractmethod
    async def __aenter__(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        raise NotImplementedError


class RateLockFactory(Protocol):
    @abstractmethod
    def __call__(
        self,
        limit_name: str,
        cooldown_period: float = 60,
        blocking: bool = True,
        lock_timeout: float = 60,
    ) -> RateLock:
        raise NotImplementedError
