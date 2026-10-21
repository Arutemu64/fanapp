from typing import ClassVar

from fanfan.application.commands.base import Command
from fanfan.core.vo.sync import SyncRunId, SyncSource


class RunSyncCommand(Command):
    subject: ClassVar[str] = "cmd.sync.run"

    sync_run_id: SyncRunId
    source: SyncSource
