from typing import ClassVar

from fanfan.core.events.base import AppEvent
from fanfan.core.vo.sync import SyncRunId, SyncSource


class SyncRequested(AppEvent):
    subject: ClassVar[str] = "sync.requested"

    sync_run_id: SyncRunId
    source: SyncSource
