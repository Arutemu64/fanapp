from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from fanfan.core.events.base import AppEvent


class JobStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    # The handler decided the job can never succeed (an unreachable user, a
    # cancelled mailing), so it was dropped without retrying.
    DISCARDED = "discarded"
    # Gave up after the last allowed attempt.
    FAILED = "failed"


class Job(BaseModel):
    """A claimed job, as handed to its handler."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    # The handler that runs it (see presentation/worker/routes).
    name: str
    # The event the job reacts to, serialized.
    payload: dict[str, Any]
    # The commit timestamp of the transaction that enqueued the job.
    created_at: datetime
    # Trace propagation headers of the producer, so the job joins its trace.
    trace_headers: dict[str, str] | None
    # Attempts so far, this one included: claiming a job counts it.
    attempts: int


@dataclass(frozen=True, slots=True)
class EventRoutes:
    """Which jobs each domain event starts: event subject → handler names.

    Built from the worker's handler registry (presentation/worker/routes) and
    injected where events are stored, so the handlers stay the single source of
    truth for who reacts to what.
    """

    jobs_by_subject: Mapping[str, tuple[str, ...]]

    def jobs_for(self, event: AppEvent) -> tuple[str, ...]:
        names = self.jobs_by_subject.get(event.subject)
        if not names:
            # A programming error, raised before the commit so the write that
            # recorded the event rolls back instead of silently losing it.
            msg = f"No job handles event {event.subject!r}"
            raise LookupError(msg)
        return names
