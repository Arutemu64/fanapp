import enum
from typing import NewType
from uuid import UUID, uuid7

SyncRunId = NewType("SyncRunId", UUID)


def generate_sync_run_id() -> SyncRunId:
    return SyncRunId(uuid7())


class SyncSource(enum.StrEnum):
    """External system a sync run pulls from."""

    COSPLAY2 = "cosplay2"
    TICKETSCLOUD = "ticketscloud"


class SyncTrigger(enum.StrEnum):
    """How a sync run was started.

    Scheduler and CLI runs execute under the system identity (no real user), so
    the trigger — not a faked user row — is what attributes them in the run log.
    """

    MANUAL = "manual"
    SCHEDULE = "schedule"
    CLI = "cli"


class SyncRunStatus(enum.StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
