from pydantic import BaseModel


class OutboxConfig(BaseModel):
    """Tuning for the outbox relay and retention (application policy).

    Lives in the application layer because the relay/retention interactors
    consume it; main/presentation populate it from env and inject it.
    """

    # How often the relay polls for undelivered events. Seconds, sub-minute OK.
    poll_interval_seconds: float = 2.0
    # Max events drained per relay tick.
    batch_size: int = 100
    # Delivered rows older than this are dropped by the retention job.
    retention_days: int = 7
