import logging

from pydantic import BaseModel

from fanfan.application.interactors.schedule.publish_schedule_updated import (
    PublishScheduleUpdated,
)
from fanfan.application.ports.gateways.schedule_events import (
    ScheduleEventGateway,
)
from fanfan.application.services.schedule_edit import ScheduleEditService
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_event import generate_schedule_event_id

# Events start at 100 and step by 100 so an organizer can later drop rows between
# them without renumbering (order is a float column). The demo seed reuses these.
ORDER_INIT = 100.0
ORDER_STEP = 100.0

logger = logging.getLogger(__name__)


class ScheduleEntry(BaseModel):
    # None for rows the organizer left numberless (breaks and other filler).
    number: int | None
    title: str
    # Seconds, as read from the spreadsheet — see REQUIRED_COLUMNS in
    # adapters/parsers/schedule.py. Sub-minute acts are expected, so this is
    # never rounded to whole minutes anywhere along the way.
    duration: int
    # None for rows with no competition nomination / programme block — breaks,
    # the opening and the closing. See _read_optional_text in the parser.
    nomination_title: str | None
    block_title: str | None


class ImportScheduleInput(BaseModel):
    schedule: list[ScheduleEntry]


class ImportSchedule:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        schedule_edit: ScheduleEditService,
        publish_schedule_updated: PublishScheduleUpdated,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_edit = schedule_edit
        self.publish_schedule_updated = publish_schedule_updated

    @staticmethod
    def _match_existing_event(
        entry: ScheduleEntry, candidates: list[ScheduleEvent]
    ) -> ScheduleEvent | None:
        """Find the event this row updates, or None to create a new one.

        Number is the only identity a spreadsheet row carries, so a numberless
        row (a break) matches nothing and is imported as a fresh event — the
        numberless events already in the schedule are left to be deleted as
        orphans. Titles are not a fallback: several breaks share one title, so
        matching on it would shuffle rows between each other.
        """
        if entry.number is None:
            return None

        return next((e for e in candidates if e.number == entry.number), None)

    async def __call__(self, data: ImportScheduleInput) -> None:
        async def mutate(current_user: User) -> None:
            orphaned_events = await self.schedule_gateway.list_all()
            order = ORDER_INIT
            for entry in data.schedule:
                existing_event = self._match_existing_event(entry, orphaned_events)
                if existing_event:
                    existing_event.update_details(
                        title=entry.title,
                        duration=entry.duration,
                        block_title=entry.block_title,
                        nomination_title=entry.nomination_title,
                        order=order,
                    )
                    await self.schedule_gateway.save(existing_event)
                    orphaned_events.remove(existing_event)
                    logger.info(
                        "Schedule event updated during import",
                        extra={
                            "event_id": str(existing_event.id),
                            "actor_id": str(current_user.id),
                        },
                    )
                else:
                    new_event = ScheduleEvent(
                        id=generate_schedule_event_id(),
                        number=entry.number,
                        title=entry.title,
                        duration=entry.duration,
                        block_title=entry.block_title,
                        nomination_title=entry.nomination_title,
                        order=order,
                        is_current=False,
                        is_skipped=False,
                    )
                    await self.schedule_gateway.add(new_event)
                    logger.info(
                        "Schedule event added during import",
                        extra={
                            "event_id": str(new_event.id),
                            "actor_id": str(current_user.id),
                        },
                    )
                order += ORDER_STEP
            for e in orphaned_events:
                await self.schedule_gateway.delete(e)
                logger.info(
                    "Orphaned schedule event deleted during import",
                    extra={
                        "event_id": str(e.id),
                        "actor_id": str(current_user.id),
                    },
                )

        await self.schedule_edit.edit(Permission.SCHEDULE_IMPORT, mutate)

        # Import rewrites the whole schedule but deliberately records no
        # ScheduleChange, so nothing reaches the outbox → NATS → SSE path the
        # schedule_mgmt interactors rely on. Broadcast here instead, or every
        # other connected client keeps a stale schedule until it reconnects.
        # Published after commit: SSE carries no committed state, and a
        # broadcast for a rolled-back import would send clients to refetch
        # a schedule that never changed.
        await self.publish_schedule_updated()
