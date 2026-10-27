from pydantic import BaseModel


class OutboxConfig(BaseModel):
    """Tuning for the outbox relay and retention (application policy).

    Lives in the application layer because the relay/retention interactors
    consume it; main/presentation populate it from env and inject it.
    """

    poll_interval_seconds: float = 10.0
    batch_size: int = 100
    retention_days: int = 7
