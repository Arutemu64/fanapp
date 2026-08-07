from dataclasses import dataclass
from datetime import datetime

from fanfan.core.events.sync import SyncRequested
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.sync import (
    SyncRunId,
    SyncRunStatus,
    SyncSource,
    generate_sync_run_id,
)
from fanfan.core.vo.user import UserId


@dataclass(slots=True, kw_only=True)
class SyncRun(AggregateRoot):
    """One execution of a vendor sync, from any trigger.

    Every sync — manual, cron or CLI — gets a row, so "last synced" on the
    organizer page reflects reality instead of only the last button press.
    ``finished_at is None`` marks a run as still active and is the predicate of
    the partial unique index that allows only one active run per source.
    """

    id: SyncRunId
    source: SyncSource
    status: SyncRunStatus
    by_user_id: UserId | None
    started_at: datetime | None
    finished_at: datetime | None
    result: str | None
    error: str | None

    @classmethod
    def create(cls, *, source: SyncSource, by_user_id: UserId | None) -> SyncRun:
        return cls(
            id=generate_sync_run_id(),
            source=source,
            status=SyncRunStatus.PENDING,
            by_user_id=by_user_id,
            started_at=None,
            finished_at=None,
            result=None,
            error=None,
        )

    def queue(self) -> None:
        # Record the request as a domain event instead of publishing it
        # directly. The UnitOfWork writes it to the outbox in the same
        # transaction as this row, so the run and its event are durable
        # together (see docs/backend.md -> Transactional outbox).
        self.record_event(SyncRequested(sync_run_id=self.id, source=self.source))

    def mark_running(self, now: datetime) -> None:
        self.status = SyncRunStatus.RUNNING
        self.started_at = now

    def mark_finished(self, result: str, now: datetime) -> None:
        self.status = SyncRunStatus.FINISHED
        self.result = result
        self.finished_at = now

    def mark_failed(self, error: str, now: datetime) -> None:
        self.status = SyncRunStatus.FAILED
        self.error = error
        self.finished_at = now
