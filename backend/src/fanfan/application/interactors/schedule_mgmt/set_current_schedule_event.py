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


class SetCurrentScheduleEventInput(BaseModel):
    event_id: ScheduleEntryId | None


class SetCurrentScheduleEvent:
    def __init__(
        self,
        schedule_gateway: ScheduleEntryGateway,
        schedule_edit: ScheduleEditService,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.schedule_edit = schedule_edit

    async def __call__(
        self, data: SetCurrentScheduleEventInput, *, actor: User | None = None
    ) -> bool:
        """Returns whether the current event changed."""

        async def already_applied() -> bool:
            current_event = await self.schedule_gateway.get_current()
            if current_event is None:
                return data.event_id is None
            return current_event.id == data.event_id

        async def mutate(_: User) -> ChangeFactory:
            previous_current_event = await self.schedule_gateway.get_current()
            if previous_current_event:
                previous_current_event.unset_current()
                await self.schedule_gateway.save(previous_current_event)

            if data.event_id is not None:
                event = await self.schedule_gateway.get_event(data.event_id)
                if event is None:
                    raise EventNotFound
                event.set_current()
                await self.schedule_gateway.save(event)
            else:
                event = None

            def build_change(ctx: AnnouncedChangeContext) -> ScheduleChange:
                return ScheduleChange.set_as_current(
                    changed_event_id=event.id if event else None,
                    previous_event_id=previous_current_event.id
                    if previous_current_event
                    else None,
                    mailing_id=ctx.mailing_id,
                    user_id=ctx.user_id,
                )

            return build_change

        outcome = await self.schedule_edit.announce(
            Permission.SCHEDULE_MANAGE,
            mutate,
            already_applied=already_applied,
            actor=actor,
        )

        logger.info(
            "Schedule event set as current",
            extra={
                "event_id": str(data.event_id) if data.event_id else None,
                "actor_id": str(outcome.user.id),
            },
        )
        return outcome.applied
