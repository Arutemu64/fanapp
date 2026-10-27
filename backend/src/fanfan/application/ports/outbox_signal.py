from typing import Protocol


class OutboxSignal(Protocol):
    """Low-latency wake-up for the outbox relay.

    A Postgres ``NOTIFY`` — fired by a trigger the moment an outbox row is
    inserted — lets the relay drain as soon as an event is enqueued instead of
    waiting for its next poll. This is a best-effort *speed* layer only: the
    relay's periodic poll stays the correctness backstop, so a missed signal (a
    listener mid-reconnect, a transport blip) costs a little latency, never an
    event. That is what keeps the at-least-once outbox guarantee intact — unlike
    a design that treats LISTEN/NOTIFY as the delivery mechanism, where a dropped
    notification silently loses the event.
    """

    def arm(self) -> None:
        """Reset the latch. Call immediately before a drain so a signal that
        arrives *during* the drain wakes the next ``wait`` rather than being
        lost between the drain and the wait."""
        ...

    async def wait(self, timeout: float) -> None:  # noqa: ASYNC109
        """Return as soon as an enqueue has been signalled since the last
        ``arm``, or after ``timeout`` seconds — whichever comes first."""
        ...
