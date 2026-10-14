import logging
from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.services.schedule_edit import ScheduleEditService
from fanfan.core.exceptions.schedule import (
    EventNotFound,
    OutdatedScheduleChange,
    ScheduleChangeNotFound,
)
from fanfan.core.models.schedule_entry import ScheduleEntry, ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_entry import ScheduleEntryId

logger = logging.getLogger(__name__)


class UndoScheduleChangeInput(BaseModel):
    schedule_change_id: ScheduleChangeId


class UndoScheduleChange:
    def __init__(
        self,
        changes_gateway: ScheduleChangeGateway,
        schedule_gateway: ScheduleEntryGateway,
        schedule_edit: ScheduleEditService,
    ) -> None:
        self.changes_gateway = changes_gateway
        self.schedule_gateway = schedule_gateway
        self.schedule_edit = schedule_edit

    async def _handle_set_as_current(
        self,
        changed_event: ScheduleEvent | None,
        previous_event: ScheduleEvent | None,
    ) -> None:
        current_event = await self.schedule_gateway.get_current()

        if changed_event != current_event:
            raise OutdatedScheduleChange

        if changed_event:
            changed_event.unset_current()
            await self.schedule_gateway.save(changed_event)

        if previous_event:
            # Undo puts the previously-current event back on stage.
            previous_event.set_current()
            await self.schedule_gateway.save(previous_event)

    async def _handle_moved(
        self,
        changed_event: ScheduleEvent,
        place_after_event: ScheduleEntry | None,
    ) -> None:
        if place_after_event:
            place_before_event = await self.schedule_gateway.get_next_by_order(
                place_after_event.order
            )
            if place_before_event:
                changed_event.place_after(place_after_event, place_before_event)
            else:
                changed_event.place_after(place_after_event, None)
        else:
            # The very first entry, not the first event: the move started ahead
            # of everything, so the event must land ahead of any block start too.
            first_entry = await self.schedule_gateway.get_first()
            changed_event.place_before_first(first_entry)

        await self.schedule_gateway.save(changed_event)

    @staticmethod
    async def _require[T](
        load: Callable[[ScheduleEntryId], Awaitable[T | None]],
        entry_id: ScheduleEntryId | None,
    ) -> T | None:
        # A null id means the change simply had no entry in that slot. A non-null
        # id that resolves to nothing is an inconsistent state, so fail loud
        # instead of silently skipping the revert below.
        if entry_id is None:
            return None
        entry = await load(entry_id)
        if entry is None:
            raise EventNotFound
        return entry

    async def __call__(self, data: UndoScheduleChangeInput) -> None:
        async def mutate(_: User) -> None:
            schedule_change = await self.changes_gateway.get_by_id(
                data.schedule_change_id
            )
            if schedule_change is None:
                raise ScheduleChangeNotFound

            changed_event = await self._require(
                self.schedule_gateway.get_event, schedule_change.changed_event_id
            )

            # The argument is the previously current event for SET_AS_CURRENT,
            # but any entry for MOVED: the one the event landed after.
            if schedule_change.type is ScheduleChangeType.SET_AS_CURRENT:
                previous_event = await self._require(
                    self.schedule_gateway.get_event, schedule_change.argument_event_id
                )
                await self._handle_set_as_current(changed_event, previous_event)

            if schedule_change.type is ScheduleChangeType.MOVED and changed_event:
                place_after_entry = await self._require(
                    self.schedule_gateway.get_entry, schedule_change.argument_event_id
                )
                await self._handle_moved(changed_event, place_after_entry)

            if schedule_change.type is ScheduleChangeType.SKIPPED and changed_event:
                changed_event.unskip()
                await self.schedule_gateway.save(changed_event)

            if schedule_change.type is ScheduleChangeType.UNSKIPPED and changed_event:
                changed_event.skip()
                await self.schedule_gateway.save(changed_event)

            schedule_change.mark_undone()
            await self.changes_gateway.delete(schedule_change)

        user = await self.schedule_edit.edit(Permission.SCHEDULE_MANAGE, mutate)

        logger.info(
            "Schedule change reverted",
            extra={
                "schedule_change_id": str(data.schedule_change_id),
                "actor_id": str(user.id),
            },
        )
