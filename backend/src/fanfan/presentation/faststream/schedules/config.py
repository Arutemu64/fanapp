from pydantic import BaseModel, field_validator


class SchedulerConfig(BaseModel):
    """Crons in the app time zone; ``None`` or a blank value disables a job.

    Vendor syncs stay off until configured. Retention jobs only delete dead
    rows, so they run nightly by default, staggered so they don't overlap.
    """

    sync_tcloud_cron: str | None = None
    sync_cosplay2_cron: str | None = None
    outbox_retention_cron: str | None = "10 4 * * *"
    notification_retention_cron: str | None = "20 4 * * *"
    expired_state_retention_cron: str | None = "30 4 * * *"

    @field_validator("*")
    @classmethod
    def _blank_disables(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            return None
        return value
