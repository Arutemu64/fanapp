from pydantic import BaseModel


class JobsConfig(BaseModel):
    """Tuning for the job worker and retention (application policy).

    Lives in the application layer because the job queue service and the
    retention interactor consume it; main/presentation populate it from env and
    inject it.
    """

    # Backstop poll interval, in seconds. Jobs are normally picked up on a
    # Postgres NOTIFY on insert (near-instant), and retries at their due time,
    # so this only bounds worst-case latency when a notification is missed
    # (listener reconnecting, transport blip). Sub-minute OK.
    poll_interval_seconds: float = 10.0
    # Jobs one worker process runs at once. Each running job holds a pooled DB
    # connection (a sync holds two), so keep it below the worker's pool ceiling.
    concurrency: int = 8
    # How long a claimed job stays invisible to other claims. The worker renews
    # it on a heartbeat while the job runs, so this bounds only how soon a job
    # whose worker died is picked up again, not how long a job may run.
    lease_seconds: float = 30.0
    # Attempts, the first included, before a failing job is given up on.
    # Generous because the send jobs spend attempts on Telegram/VK
    # flood-control retry-afters.
    max_attempts: int = 20
    # Finished jobs older than this are dropped by the retention job.
    retention_days: int = 7
