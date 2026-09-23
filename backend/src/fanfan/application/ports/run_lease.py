from typing import Protocol


class RunLease(Protocol):
    """Proof that this worker, and no other, is doing the work named by a key.

    A redelivered trigger cannot tell a dead worker from a live one that merely
    missed its NATS heartbeats. The lease can: it is held for as long as the
    holding worker is alive and released the moment it is gone, so taking it
    proves the previous holder stopped.
    """

    async def try_acquire(self, key: str) -> bool:
        """Take the lease for ``key``; False if a live worker already holds it."""
        ...

    async def release(self) -> None:
        """Give the lease up. A no-op when none is held."""
        ...
