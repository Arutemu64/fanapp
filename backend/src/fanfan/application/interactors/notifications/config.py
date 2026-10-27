from pydantic import BaseModel


class NotificationConfig(BaseModel):
    """Retention policy for stored notifications (application policy).

    Lives in the application layer because the retention interactor consumes it;
    main/presentation populate it from env and inject it.
    """

    retention_days: int = 30
