from pydantic import BaseModel


class OutboxConfig(BaseModel):
    """Tuning for the outbox relay and retention (application policy).

    Lives in the application layer because the relay/retention interactors
    consume it; main/presentation populate it from env and inject it.
    """

    # Backstop poll interval, in seconds. Delivery is normally driven by a
    # Postgres NOTIFY on insert (near-instant), so this only bounds worst-case
    # latency when a notification is missed (listener reconnecting, transport
    # blip) — it no longer sets the everyday latency, so it can be relaxed to
    # keep idle DB load low. Sub-minute OK.
    poll_interval_seconds: float = 10.0
    # Max events drained per relay tick.
    batch_size: int = 100
    # Delivered rows older than this are dropped by the retention job.
    retention_days: int = 7
