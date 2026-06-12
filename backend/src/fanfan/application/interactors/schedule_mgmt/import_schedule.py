import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.schedule_events import (
    ScheduleEventGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.vo.permission import PermissionName, Permissions
from fanfan.core.vo.schedule_event import generate_schedule_event_id

ORDER_INIT = 100.0
ORDER_STEP = 100.0

logger = logging.getLogger(__name__)


class ScheduleEntry(BaseModel):
    public_number: int
    title: str
    duration: int
    nomination_title: str
    block_title: str


class ImportScheduleInput(BaseModel):
    schedule: list[ScheduleEntry]


class ImportSchedule:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        uow: UnitOfWork,
        current_user_provider: CurrentUserProvider,
        user_gateway: UserGateway,
        perm_service: PermissionService,
    ):
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.uow = uow
        self.schedule_gateway = schedule_gateway
        self.perm_service = perm_service

    async def __call__(self, data: ImportScheduleInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, perm_name=PermissionName(Permissions.SCHEDULE_IMPORT)
        )
        orphaned_events = await self.schedule_gateway.list_all()
        order = ORDER_INIT
        for entry in data.schedule:
            existing_event = next(
                (e for e in orphaned_events if e.public_number == entry.public_number),
                None,
            )
            if existing_event:
                # Update event
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
                    "Existing event was updated",
                    extra={"existing_event": existing_event},
                )
            else:
                # Create new event
                new_event = ScheduleEvent(
                    id=generate_schedule_event_id(),
                    public_number=entry.public_number,
                    title=entry.title,
                    duration=entry.duration,
                    block_title=entry.block_title,
                    nomination_title=entry.nomination_title,
                    order=order,
                    is_current=False,
                    is_skipped=False,
                )
                await self.schedule_gateway.add(new_event)
                logger.info("New event was added", extra={"new_event": new_event})
            order += ORDER_STEP
        for e in orphaned_events:
            await self.schedule_gateway.delete(e)
            logger.info("Orphaned event was deleted", extra={"deleted_event": e})
        await self.uow.commit()
