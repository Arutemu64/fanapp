from typing import Protocol


class JobSignal(Protocol):
    """Low-latency wake-up for the job worker.

    A Postgres ``NOTIFY`` — fired by a trigger the moment a job is inserted —
    lets the worker claim it as soon as it is enqueued instead of waiting for
    its next poll. This is a best-effort *speed* layer only: the
    worker's periodic poll stays the correctness backstop, so a missed signal (a
    listener mid-reconnect, a transport blip) costs a little latency, never a
    job. That is what keeps the at-least-once guarantee intact — unlike a design
    that treats LISTEN/NOTIFY as the delivery mechanism, where a dropped
    notification silently loses the job.
    """

    def arm(self) -> None:
        """Reset the latch. Call immediately before a claim so a signal that
        arrives *during* the claim wakes the next ``wait`` rather than being
        lost between the claim and the wait."""
        ...

    # ASYNC109 is suppressed below: the timeout is part of this primitive's
    # contract — wait for a signal, but no longer than the caller's deadline —
    # so the wait owns it rather than each caller wrapping the call in a block.
    async def wait(self, timeout: float) -> None:  # noqa: ASYNC109
        """Return as soon as an enqueue has been signalled since the last
        ``arm``, or after ``timeout`` seconds — whichever comes first."""
        ...
