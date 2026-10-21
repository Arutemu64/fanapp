import asyncio


class RateLimiter:
    """Spaces calls evenly so at most ``per_second`` start in any second.

    Each caller claims the next free slot and sleeps until it, so concurrent
    senders share one provider quota instead of each discovering it through
    429s and backing off. Even spacing rather than a bucket that allows a burst:
    providers count requests per second, and a burst at the top of a second is
    exactly what trips their flood control. Per process; the faststream
    service runs as a single container, so this is the whole app's rate.
    """

    def __init__(self, per_second: float) -> None:
        self._interval = 1 / per_second
        self._next_slot = 0.0

    async def wait(self) -> None:
        # No await between reading and advancing the slot, so concurrent
        # callers on one event loop never claim the same slot.
        now = asyncio.get_running_loop().time()
        slot = max(now, self._next_slot)
        self._next_slot = slot + self._interval
        delay = slot - now
        if delay > 0:
            await asyncio.sleep(delay)
