import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.services.schedule_edit import (
    AnnouncedChangeContext,
    ChangeFactory,
    ScheduleEditService,
)
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_entry import ScheduleEntryId

logger = logging.getLogger(__name__)


class MoveScheduleEventInput(BaseModel):
    event_id: ScheduleEntryId
    # None moves the event to the top of the schedule.
    place_after_entry_id: ScheduleEntryId | None


class MoveScheduleEvent:
    def __init__(
        self,
        schedule_gateway: ScheduleEntryGateway,
        schedule_edit: ScheduleEditService,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_edit = schedule_edit

    async def _place_after(
        self, event: ScheduleEvent, place_after_entry_id: ScheduleEntryId
    ) -> None:
        place_after_entry = await self.schedule_gateway.get_entry(place_after_entry_id)
        if place_after_entry is None:
            raise EventNotFound
        place_before_entry = await self.schedule_gateway.get_next_by_order(
            place_after_entry.order
        )
        event.place_after(place_after_entry, place_before_entry)

    async def __call__(self, data: MoveScheduleEventInput) -> None:
        async def already_applied() -> bool:
            event = await self.schedule_gateway.get_event(data.event_id)
            if event is None:
                return False
            previous_entry = await self.schedule_gateway.get_previous_by_order(
                event.order
            )
            if previous_entry is None:
                return data.place_after_entry_id is None
            return previous_entry.id == data.place_after_entry_id

        async def mutate(_: User) -> ChangeFactory:
            event = await self.schedule_gateway.get_event(data.event_id)
            if event is None:
                raise EventNotFound

            previous_entry = await self.schedule_gateway.get_previous_by_order(
                event.order
            )

            if data.place_after_entry_id is None:
                event.place_before_first(await self.schedule_gateway.get_first())
            else:
                await self._place_after(event, data.place_after_entry_id)
            await self.schedule_gateway.save(event)

            def build_change(ctx: AnnouncedChangeContext) -> ScheduleChange:
                return ScheduleChange.moved(
                    event_id=event.id,
                    previous_entry_id=previous_entry.id if previous_entry else None,
                    mailing_id=ctx.mailing_id,
                    user_id=ctx.user_id,
                    next_event_changed=ctx.next_event_changed,
                )

            return build_change

        user = await self.schedule_edit.announce(
            Permission.SCHEDULE_MANAGE, mutate, already_applied=already_applied
        )

        logger.info(
            "Schedule event moved",
            extra={
                "event_id": str(data.event_id),
                "place_after_entry_id": str(data.place_after_entry_id),
                "actor_id": str(user.id),
            },
        )
