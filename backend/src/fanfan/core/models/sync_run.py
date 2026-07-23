from dataclasses import dataclass
from datetime import datetime

from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.sync import SyncRunId, SyncRunStatus, SyncSource, SyncTrigger
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class SyncRun(AggregateRoot):
    """One finished external-sync attempt (append-only audit record).

    The "last synced" timestamp shown to orgs is derived from the newest
    completed run per source — there is deliberately no mutable status row.
    """

    id: SyncRunId
    source: SyncSource
    trigger: SyncTrigger
    status: SyncRunStatus
    # None for system-triggered runs (scheduler / CLI).
    started_by_user_id: UserId | None
    started_at: datetime
    finished_at: datetime
    error_message: str | None
