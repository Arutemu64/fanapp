from typing import Protocol


class ExpiredStatePurger(Protocol):
    """Deletes short-lived state past its expiry: sessions, email codes, rate
    limits and cooldowns. Readers already ignore expired rows, so this only
    reclaims space.
    """

    async def purge_expired(self) -> int:
        """Return how many rows were deleted."""
        ...
