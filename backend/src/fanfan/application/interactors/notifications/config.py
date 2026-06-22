from pydantic import BaseModel


class NotificationConfig(BaseModel):
    """Retention policy for stored notifications (application policy).

    Lives in the application layer because the retention interactor consumes it;
    main/presentation populate it from env and inject it.
    """

    # Notifications older than this are dropped by the retention job. In-app
    # notifications (schedule changes, mailings) lose relevance shortly after the
    # convention, so a month-long window keeps recent history while capping
    # unbounded per-user growth.
    retention_days: int = 30
