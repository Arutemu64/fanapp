import enum
from typing import NewType
from uuid import UUID, uuid7

SyncRunId = NewType("SyncRunId", UUID)


def generate_sync_run_id() -> SyncRunId:
    return SyncRunId(uuid7())


class SyncSource(enum.StrEnum):
    """External system a sync run pulls from.

    The value doubles as the URL path segment (``POST /sync/{source}``) and the
    stored column value, so it is part of both the API and the DB contract.
    """

    COSPLAY2 = "cosplay2"
    TCLOUD = "tcloud"


class SyncRunStatus(enum.StrEnum):
    # Requested over HTTP, waiting for the NATS consumer to pick it up. Runs
    # started by cron or the CLI skip this state — they begin as RUNNING.
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
