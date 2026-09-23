from contextlib import AbstractAsyncContextManager
from typing import Protocol


class Cooldown(Protocol):
    """Allows one successful run per key per cooldown window.

    ``claim`` takes the window atomically on entry, so a concurrent caller for
    the same key fails fast with CooldownActive instead of queueing behind the
    first. A block that raises gives the claim back, so a failed operation (an
    SMTP error, say) can be retried at once instead of burning the window.
    """

    def claim(self, key: str, seconds: int) -> AbstractAsyncContextManager[None]:
        """Raise CooldownActive(retry_after) if ``key`` is still cooling down."""
        ...
