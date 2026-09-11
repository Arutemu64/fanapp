from typing import Protocol

from fanfan.core.vo.user import UserId


class PresenceGateway(Protocol):
    """Tracks which users are currently connected, as a coarse live signal.

    Presence is derived from the SSE connection a client holds: the stream route
    refreshes a user's marker on connect and on every heartbeat tick, and a
    marker ages out once refreshes stop (a closed tab, a dropped mobile
    connection). It is intentionally ephemeral (Redis-backed, never persisted) —
    an approximate "who's online right now", not an audit of last-seen times.
    """

    async def mark_online(self, user_id: UserId) -> None: ...

    async def count_online(self) -> int: ...
