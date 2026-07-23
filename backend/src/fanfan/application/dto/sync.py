from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.sync import SyncRunId, SyncRunStatus, SyncSource, SyncTrigger
from fanfan.core.vo.user import UserId


class SyncRunUserDTO(BaseModel):
    id: UserId
    username: str


class SyncRunDTO(BaseModel):
    id: SyncRunId
    source: SyncSource
    trigger: SyncTrigger
    status: SyncRunStatus
    started_at: datetime
    finished_at: datetime
    error_message: str | None
    started_by: SyncRunUserDTO | None


class SyncSourceStatusDTO(BaseModel):
    source: SyncSource
    last_success_at: datetime | None
    recent_runs: list[SyncRunDTO]


class SyncStatusDTO(BaseModel):
    sources: list[SyncSourceStatusDTO]
