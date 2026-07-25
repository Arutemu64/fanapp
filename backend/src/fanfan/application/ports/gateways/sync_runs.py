from datetime import datetime
from typing import Protocol

from fanfan.application.dto.sync import SyncRunDTO
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.sync import SyncRunId, SyncSource


class SyncRunGateway(Protocol):
    async def add(self, run: SyncRun) -> None:
        """Insert a run.

        Raises ``SyncAlreadyRunning`` when another run for the same source is
        still active (the ``uq_sync_runs_active`` partial unique index).
        """
        ...

    async def get(self, run_id: SyncRunId) -> SyncRun | None: ...
    async def save(self, run: SyncRun) -> None: ...

    async def get_active(self, source: SyncSource) -> SyncRun | None:
        """The unfinished run for a source, if any."""
        ...

    async def fail_stale(
        self, source: SyncSource, *, older_than: datetime, error: str
    ) -> int:
        """Terminate active runs for a source that started before ``older_than``.

        Returns the number of rows reaped. Used to unwedge the partial unique
        index after a worker died mid-run.
        """
        ...

    async def read_latest_by_source(self) -> dict[SyncSource, SyncRunDTO]: ...
