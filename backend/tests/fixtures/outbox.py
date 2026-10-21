from typing import Any

from dishka import AsyncContainer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import JobORM
from fanfan.application.dto.jobs import EventRoutes
from fanfan.core.events.base import AppEvent


class Outbox:
    """Reads back the events a test enqueued, from the jobs they became.

    The UnitOfWork stores one job per handler of an event, so an event with
    three handlers is three rows. Tests assert on events, not handlers, so each
    event is read from its first handler's job only, in creation order.
    """

    def __init__(self, session: AsyncSession, routes: EventRoutes) -> None:
        self.session = session
        self.first_job_to_subject = {
            names[0]: subject for subject, names in routes.jobs_by_subject.items()
        }

    @classmethod
    async def resolve(cls, container: AsyncContainer) -> Outbox:
        return cls(
            session=await container.get(AsyncSession),
            routes=await container.get(EventRoutes),
        )

    async def events(self) -> list[tuple[str, dict[str, Any]]]:
        rows = await self.session.scalars(
            select(JobORM).order_by(JobORM.created_at, JobORM.id)
        )
        events: list[tuple[str, dict[str, Any]]] = []
        for row in rows:
            subject = self.first_job_to_subject.get(row.name)
            if subject is not None:
                events.append((subject, row.payload))
        return events

    async def events_of[E: AppEvent](self, event_type: type[E]) -> list[E]:
        return [
            event_type.model_validate(payload)
            for subject, payload in await self.events()
            if subject == event_type.subject
        ]
