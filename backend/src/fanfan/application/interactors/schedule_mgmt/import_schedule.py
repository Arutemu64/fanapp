import logging

from pydantic import BaseModel

from fanfan.application.interactors.schedule.publish_schedule_updated import (
    PublishScheduleUpdated,
)
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.schedule_edit import ScheduleEditService
from fanfan.core.models.schedule_entry import (
    ScheduleBlockStart,
    ScheduleEntry,
    ScheduleEvent,
)
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id

ORDER_INIT = 100.0
ORDER_STEP = 100.0

logger = logging.getLogger(__name__)


class ScheduleEventRow(BaseModel):
    number: int | None
    title: str
    duration: int
    nomination_title: str | None


class ScheduleBlockRow(BaseModel):
    title: str


type ScheduleRow = ScheduleEventRow | ScheduleBlockRow


def build_schedule_entry(row: ScheduleRow, order: float) -> ScheduleEntry:
    """A fresh entry for a row; the import and the demo seed share it."""
    if isinstance(row, ScheduleBlockRow):
        return ScheduleBlockStart(
            id=generate_schedule_entry_id(), title=row.title, order=order
        )
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=row.number,
        title=row.title,
        duration=row.duration,
        nomination_title=row.nomination_title,
        order=order,
        is_current=False,
        is_skipped=False,
    )


class ImportScheduleInput(BaseModel):
    schedule: list[ScheduleRow]


class ImportSchedule:
    def __init__(
        self,
        current_user_provider: CurrentUserProvider,
        schedule_gateway: ScheduleEntryGateway,
        schedule_edit: ScheduleEditService,
        publish_schedule_updated: PublishScheduleUpdated,
    ) -> None:
        self.current_user_provider = current_user_provider
        self.schedule_gateway = schedule_gateway
        self.schedule_edit = schedule_edit
        self.publish_schedule_updated = publish_schedule_updated

    @staticmethod
    def _match_existing_entry(
        row: ScheduleRow, candidates: list[ScheduleEntry]
    ) -> ScheduleEntry | None:
        """Find the entry this row updates, or None to create a new one.

        Number is the only identity an event row carries, so a numberless row (a
        break) matches nothing and is imported as a fresh event — the numberless
        events already in the schedule are left to be deleted as orphans.
        Titles are not a fallback for events: several breaks share one title,
        so matching on it would shuffle rows between each other.

        A block row has no number, so it matches a block start by title. That
        keeps the block's id, and with it the schedule changes that recorded a
        move to the block's start, across a re-import.
        """
        if isinstance(row, ScheduleBlockRow):
            return next(
                (
                    e
                    for e in candidates
                    if isinstance(e, ScheduleBlockStart) and e.title == row.title
                ),
                None,
            )

        if row.number is None:
            return None

        return next(
            (
                e
                for e in candidates
                if isinstance(e, ScheduleEvent) and e.number == row.number
            ),
            None,
        )

    async def __call__(self, data: ImportScheduleInput) -> None:
        current_user = await self.current_user_provider.require_user()

        async def mutate() -> None:
            orphaned_entries = await self.schedule_gateway.list_all()
            order = ORDER_INIT
            for row in data.schedule:
                existing_entry = self._match_existing_entry(row, orphaned_entries)
                if existing_entry is None:
                    new_entry = build_schedule_entry(row, order)
                    await self.schedule_gateway.add(new_entry)
                    logger.info(
                        "Schedule entry added during import",
                        extra={
                            "entry_id": str(new_entry.id),
                            "actor_id": str(current_user.id),
                        },
                    )
                else:
                    if isinstance(existing_entry, ScheduleBlockStart):
                        existing_entry.order = order
                    elif isinstance(row, ScheduleEventRow):
                        existing_entry.update_details(
                            title=row.title,
                            duration=row.duration,
                            nomination_title=row.nomination_title,
                            order=order,
                        )
                    await self.schedule_gateway.save(existing_entry)
                    orphaned_entries.remove(existing_entry)
                    logger.info(
                        "Schedule entry updated during import",
                        extra={
                            "entry_id": str(existing_entry.id),
                            "actor_id": str(current_user.id),
                        },
                    )
                order += ORDER_STEP
            for e in orphaned_entries:
                await self.schedule_gateway.delete(e)
                logger.info(
                    "Orphaned schedule entry deleted during import",
                    extra={
                        "entry_id": str(e.id),
                        "actor_id": str(current_user.id),
                    },
                )

        await self.schedule_edit.edit(current_user, Permission.SCHEDULE_SETUP, mutate)

        await self.publish_schedule_updated()
