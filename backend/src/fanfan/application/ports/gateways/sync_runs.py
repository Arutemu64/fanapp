from datetime import datetime
from typing import Protocol

from fanfan.application.dto.sync import SyncRunDTO
from fanfan.core.models.sync_run import SyncRun
from fanfan.core.vo.sync import SyncSource


class SyncRunGateway(Protocol):
    async def add(self, run: SyncRun) -> None: ...

    # Read projections (return DTOs, not aggregates)
    async def read_last_completed_at(self, source: SyncSource) -> datetime | None: ...

    async def read_recent_runs(
        self, source: SyncSource, limit: int
    ) -> list[SyncRunDTO]: ...
