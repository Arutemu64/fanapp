from typing import Protocol


class RateLimiter(Protocol):
    """Counts attempts against a key inside a fixed time window.

    Unlike RateLockFactory (which serializes callers and burns a cooldown only
    on a *successful* run), this limiter counts *every* call and locks the key
    once the count goes over the limit. That makes it the right tool for things
    like login brute-force, where wrong guesses are exactly what we want to
    penalize.
    """

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> None:
        """Record one attempt against ``key``.

        Raises TooManyAttempts(retry_after) once the number of attempts within
        the current window exceeds ``limit``.
        """
        ...

    async def reset(self, key: str) -> None:
        """Clear the counter for ``key`` (e.g. after a successful login)."""
        ...
