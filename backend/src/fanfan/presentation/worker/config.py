from pydantic import BaseModel


class WorkerConfig(BaseModel):
    # Jobs one worker process runs at once. Each holds a DB session while it
    # runs, so keep it at or below the worker's DB__POOL_SIZE + DB__MAX_OVERFLOW.
    concurrency: int = 8
    # Finished jobs (succeeded, failed, cancelled, aborted) older than this are
    # deleted by the daily prune task.
    job_retention_days: int = 7
