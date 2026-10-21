from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, TypedDict

from procrastinate import App
from procrastinate.jobs import Job
from procrastinate.tasks import Task
from psycopg import AsyncConnection

from fanfan.adapters.debug.tracing import current_trace_headers
from fanfan.core.events.base import Message

# The tasks each message subject fans out to, one job per task. Declared by the
# worker's subscribers and handed in by the composition root (main/ioc/queue.py),
# so this adapter never imports the presentation layer.
type MessageRoutes = Mapping[str, Sequence[Task[Any, Any, Any]]]


class JobArgs(TypedDict):
    """The keyword arguments every subscriber task is called with."""

    # Message.model_dump(mode="json"), validated back by the subscriber.
    message: dict[str, Any]
    # When the producing transaction committed, ISO 8601. A subscriber that
    # must not act on a stale message checks it.
    occurred_at: str
    # Sentry propagation headers of the producer, so the job joins its trace.
    trace_headers: dict[str, str] | None


class UnroutedMessageError(LookupError):
    """A message no task subscribes to: it would be queued and never run."""


class ProcrastinateJobQueue:
    """Writes messages as Procrastinate jobs on the caller's connection.

    The INSERT runs inside the caller's open transaction, so the jobs commit or
    roll back with the change that produced them (ADR-0041).
    https://procrastinate.readthedocs.io/en/stable/howto/production/external_connection.html
    """

    def __init__(self, app: App, routes: MessageRoutes) -> None:
        self.app = app
        self.routes = routes

    async def enqueue(
        self, connection: AsyncConnection[Any], messages: Sequence[Message]
    ) -> None:
        occurred_at = datetime.now(UTC).isoformat()
        trace_headers = current_trace_headers() or None
        jobs: list[Job] = []
        for message in messages:
            tasks = self.routes.get(message.subject)
            if not tasks:
                msg = f"No task subscribes to {message.subject!r}"
                raise UnroutedMessageError(msg)
            args = JobArgs(
                message=message.model_dump(mode="json"),
                occurred_at=occurred_at,
                trace_headers=trace_headers,
            )
            # configure() carries each task's own queue, priority and locks.
            jobs.extend(task.configure(task_kwargs=dict(args)).job for task in tasks)
        # One round trip for the whole commit, however large the fan-out.
        await self.app.job_manager.batch_defer_jobs_async(jobs, connection=connection)
