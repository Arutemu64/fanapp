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
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_entry import ScheduleEntryId

logger = logging.getLogger(__name__)


class MoveScheduleEventInput(BaseModel):
    event_id: ScheduleEntryId
    place_after_entry_id: ScheduleEntryId


class MoveScheduleEvent:
    def __init__(
        self,
        schedule_gateway: ScheduleEntryGateway,
        schedule_edit: ScheduleEditService,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_edit = schedule_edit

    async def __call__(self, data: MoveScheduleEventInput) -> None:
        async def mutate(_: User) -> ChangeFactory:
            event = await self.schedule_gateway.get_event(data.event_id)
            if event is None:
                raise EventNotFound

            # Any entry: a block start as the anchor moves the event to the top
            # of that block.
            place_after_event = await self.schedule_gateway.get_entry(
                data.place_after_entry_id
            )
            if place_after_event is None:
                raise EventNotFound
            place_before_event = await self.schedule_gateway.get_next_by_order(
                place_after_event.order
            )
            previous_entry = await self.schedule_gateway.get_previous_by_order(
                event.order
            )

            event.place_after(place_after_event, place_before_event)
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

        user = await self.schedule_edit.announce(Permission.SCHEDULE_MANAGE, mutate)

        logger.info(
            "Schedule event moved",
            extra={
                "event_id": str(data.event_id),
                "place_after_entry_id": str(data.place_after_entry_id),
                "actor_id": str(user.id),
            },
        )
