import logging

from pydantic import BaseModel

from fanfan.application.interactors.schedule.publish_schedule_updated import (
    PublishScheduleUpdated,
)
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.services.schedule_edit import ScheduleEditService
from fanfan.core.models.schedule_entry import (
    ScheduleBlockStart,
    ScheduleEntry,
    ScheduleEvent,
)
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id

# Entries start at 100 and step by 100 so an organizer can later drop rows between
# them without renumbering (order is a float column). The demo seed reuses these.
ORDER_INIT = 100.0
ORDER_STEP = 100.0

logger = logging.getLogger(__name__)


class ScheduleEventRow(BaseModel):
    # None for rows the organizer left numberless (breaks and other filler).
    number: int | None
    title: str
    # Seconds, as read from the spreadsheet — see REQUIRED_COLUMNS in
    # adapters/parsers/schedule.py. Sub-minute acts are expected, so this is
    # never rounded to whole minutes anywhere along the way.
    duration: int
    # None for rows with no competition nomination — breaks, the opening and
    # the closing. See _read_optional_text in the parser.
    nomination_title: str | None


class ScheduleBlockRow(BaseModel):
    # Starts a block: every row after it, up to the next block row, is in it.
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
        schedule_gateway: ScheduleEntryGateway,
        schedule_edit: ScheduleEditService,
        publish_schedule_updated: PublishScheduleUpdated,
    ) -> None:
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
        async def mutate(current_user: User) -> None:
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
                    # Matching pairs an event row only with an event and a
                    # block row only with a block start, whose title matched.
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

        await self.schedule_edit.edit(Permission.SCHEDULE_IMPORT, mutate)

        # Import rewrites the whole schedule but deliberately records no
        # ScheduleChange, so nothing reaches the jobs → worker → SSE path the
        # schedule_mgmt interactors rely on. Broadcast here instead, or every
        # other connected client keeps a stale schedule until it reconnects.
        # Published after commit: SSE carries no committed state, and a
        # live update for a rolled-back import would send clients to refetch
        # a schedule that never changed.
        await self.publish_schedule_updated()
