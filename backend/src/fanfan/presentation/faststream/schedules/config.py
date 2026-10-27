from pydantic import BaseModel


class SchedulerConfig(BaseModel):
    sync_tcloud_cron: str | None = None
    sync_cosplay2_cron: str | None = None
    outbox_retention_cron: str | None = None
    notification_retention_cron: str | None = None
    expired_state_retention_cron: str | None = None
