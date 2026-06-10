from pydantic import BaseModel


class SchedulerConfig(BaseModel):
    # Cron expressions for periodic sync jobs (see .env.example for env keys).
    # None disables the job (default) — opt in per job via env.
    sync_tcloud_cron: str | None = None
    sync_cosplay2_cron: str | None = None
    # When to purge delivered outbox rows (retention age lives in OutboxConfig).
    outbox_retention_cron: str | None = None
