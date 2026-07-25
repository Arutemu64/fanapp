from datetime import datetime

from pydantic import BaseModel

from fanfan.core.vo.sync import SyncRunId, SyncRunStatus, SyncSource


class SyncRunDTO(BaseModel):
    """A sync run as shown to an organizer.

    Deliberately omits ``by_user_id``: the row records who triggered the run for
    the audit trail, but the page only answers "is the data fresh, and did the
    last run succeed?", which status and timestamps already cover. Keeping the
    actor off the wire avoids a users join and any handling of the system user
    id on the frontend.
    """

    id: SyncRunId
    source: SyncSource
    status: SyncRunStatus
    started_at: datetime | None
    finished_at: datetime | None
    result: str | None
    error: str | None


class SyncSourceStatusDTO(BaseModel):
    source: SyncSource
    # False when the vendor is not configured for this deployment, so the UI can
    # disable a button that could only ever fail.
    available: bool
    last_run: SyncRunDTO | None
