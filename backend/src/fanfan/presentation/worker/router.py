from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from dishka import AsyncContainer

from fanfan.application.dto.jobs import EventRoutes, Job
from fanfan.core.events.base import AppEvent

type HandlerFunc[E: AppEvent] = Callable[[E, Job, AsyncContainer], Awaitable[None]]


class RetryJob(Exception):
    """Raised by a handler to run the job again once ``delay`` has passed.

    For a delay the handler knows, such as a flood-control retry-after; any
    other exception retries with the queue's own backoff.
    """

    def __init__(self, delay: timedelta, reason: str) -> None:
        super().__init__(reason)
        self.delay = delay
        self.reason = reason


class DiscardJob(Exception):
    """Raised by a handler to drop the job: retrying can never make it succeed."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class JobHandler:
    name: str
    event_type: type[AppEvent]
    func: HandlerFunc[Any]

    async def __call__(self, job: Job, container: AsyncContainer) -> None:
        event = self.event_type.model_validate(job.payload)
        await self.func(event, job, container)


class JobRouter:
    """Maps job names to handlers, and events to the jobs they start.

    A handler runs inside its own REQUEST scope and resolves what it needs from
    the container it is handed, like the cron jobs (presentation/scheduler).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def handler[E: AppEvent](
        self, event_type: type[E], *, name: str
    ) -> Callable[[HandlerFunc[E]], HandlerFunc[E]]:
        """Register a handler run once for every ``event_type`` event.

        ``name`` is stored on every job row, so renaming a handler strands its
        pending jobs: they fail as unknown until retention drops them.
        """

        def register(func: HandlerFunc[E]) -> HandlerFunc[E]:
            self._add(JobHandler(name=name, event_type=event_type, func=func))
            return func

        return register

    def include(self, other: JobRouter) -> None:
        for handler in other._handlers.values():
            self._add(handler)

    def get(self, name: str) -> JobHandler | None:
        return self._handlers.get(name)

    def routes(self) -> EventRoutes:
        jobs_by_subject: dict[str, tuple[str, ...]] = {}
        for handler in self._handlers.values():
            subject = handler.event_type.subject
            jobs_by_subject[subject] = (*jobs_by_subject.get(subject, ()), handler.name)
        return EventRoutes(jobs_by_subject=jobs_by_subject)

    def _add(self, handler: JobHandler) -> None:
        if handler.name in self._handlers:
            msg = f"Job handler {handler.name!r} is registered twice"
            raise ValueError(msg)
        self._handlers[handler.name] = handler
