from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CachedSchedule:
    """A rendered schedule response plus the version token identifying it.

    ``payload`` is the serialized ``GetScheduleOutput`` JSON, cached whole so a
    read serves stored bytes instead of re-querying and re-serializing. ``etag``
    is a strong content hash of that payload, carried alongside so a conditional
    request can be answered without rehashing the body (ADR-0014).
    """

    etag: str
    payload: str


class ScheduleCacheGateway(Protocol):
    """Caches the universal schedule response, keyed to nothing (one entry).

    The schedule is identical for every viewer and changes only on operator
    edits, so a single cached entry serves everyone. Mutating interactors call
    ``invalidate`` after they commit, so a read never serves an edit-stale body.
    """

    async def get(self) -> CachedSchedule | None: ...

    async def set(self, cached: CachedSchedule) -> None: ...

    async def invalidate(self) -> None: ...
