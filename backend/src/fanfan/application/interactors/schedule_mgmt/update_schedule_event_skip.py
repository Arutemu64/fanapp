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


class UpdateScheduleEventSkipInput(BaseModel):
    event_id: ScheduleEventId
    is_skipped: bool


class UpdateScheduleEventSkip:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        schedule_edit: ScheduleEditService,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_edit = schedule_edit

    async def __call__(self, data: UpdateScheduleEventSkipInput) -> None:
        async def mutate(_: User) -> ChangeFactory:
            event = await self.schedule_gateway.get_by_id(data.event_id)
            if event is None:
                raise EventNotFound

            if data.is_skipped:
                event.skip()
            else:
                event.unskip()
            await self.schedule_gateway.save(event)

            def build_change(ctx: AnnouncedChangeContext) -> ScheduleChange:
                factory = (
                    ScheduleChange.skipped
                    if event.is_skipped
                    else ScheduleChange.unskipped
                )
                return factory(
                    event_id=event.id,
                    mailing_id=ctx.mailing_id,
                    user_id=ctx.user_id,
                    next_event_changed=ctx.next_event_changed,
                )

            return build_change

        user = await self.schedule_edit.announce(Permission.SCHEDULE_MANAGE, mutate)

        logger.info(
            "Schedule event skip updated",
            extra={
                "event_id": str(data.event_id),
                "is_skipped": data.is_skipped,
                "actor_id": str(user.id),
            },
        )
