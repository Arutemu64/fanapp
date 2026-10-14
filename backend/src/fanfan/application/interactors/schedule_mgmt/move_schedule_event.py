import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.schedule_events import (
    ScheduleEventGateway,
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
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class MoveScheduleEventInput(BaseModel):
    event_id: ScheduleEventId
    place_after_event_id: ScheduleEventId


class MoveScheduleEvent:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        schedule_edit: ScheduleEditService,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_edit = schedule_edit

    async def __call__(self, data: MoveScheduleEventInput) -> None:
        async def mutate(_: User) -> ChangeFactory:
            event = await self.schedule_gateway.get_by_id(data.event_id)
            if event is None:
                raise EventNotFound

            place_after_event = await self.schedule_gateway.get_by_id(
                data.place_after_event_id
            )
            if place_after_event is None:
                raise EventNotFound
            place_before_event = await self.schedule_gateway.get_next_by_order(
                place_after_event.order
            )
            previous_event = await self.schedule_gateway.get_previous_by_order(
                event.order
            )

            event.place_after(place_after_event, place_before_event)
            await self.schedule_gateway.save(event)

            def build_change(ctx: AnnouncedChangeContext) -> ScheduleChange:
                return ScheduleChange.moved(
                    event_id=event.id,
                    previous_event_id=previous_event.id if previous_event else None,
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
                "place_after_event_id": str(data.place_after_event_id),
                "actor_id": str(user.id),
            },
        )
