from pydantic import BaseModel


class SchedulerConfig(BaseModel):
    # Cron expressions for the periodic jobs (see .env.example for env keys):
    # five-field crontab, NATS's six-field form with leading seconds, or a
    # descriptor such as @daily or @every 1h. None disables the job (default) —
    # opt in per job via env.
    sync_tcloud_cron: str | None = None
    sync_cosplay2_cron: str | None = None
    # When to purge delivered outbox rows (retention age lives in OutboxConfig).
    outbox_retention_cron: str | None = None
    # When to purge old notifications (retention age lives in NotificationConfig).
    notification_retention_cron: str | None = None
