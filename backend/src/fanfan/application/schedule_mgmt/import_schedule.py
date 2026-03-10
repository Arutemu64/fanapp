import logging

from pydantic import BaseModel

from fanfan.adapters.db.gateways.schedule_events import ScheduleEventGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.vo.schedule_event import ScheduleEventPublicNumber
from fanfan.core.vo.user import UserRole

ORDER_INIT = 100.0
ORDER_STEP = 100.0

logger = logging.getLogger(__name__)


class ScheduleEntry(BaseModel):
    public_number: ScheduleEventPublicNumber
    title: str
    duration: int
    nomination_title: str
    block_title: str


class ImportScheduleCommand(BaseModel):
    schedule: list[ScheduleEntry]


class ImportSchedule:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        uow: UnitOfWork,
        id_provider: IdProvider,
        user_gateway: UserGateway,
    ):
        self.user_gateway = user_gateway
        self.id_provider = id_provider
        self.uow = uow
        self.schedule_gateway = schedule_gateway

    async def __call__(self, data: ImportScheduleCommand) -> None:
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound
        if current_user.role is not UserRole.ORG:
            raise AccessDenied
        orphaned_events = await self.schedule_gateway.get_all_events()
        order = ORDER_INIT
        async with self.uow:
            for entry in data.schedule:
                existing_event = next(
                    (
                        e
                        for e in orphaned_events
                        if e.public_number == entry.public_number
                    ),
                    None,
                )
                if existing_event:
                    # Update event
                    existing_event.title = entry.title
                    existing_event.duration = entry.duration
                    existing_event.block_title = entry.block_title
                    existing_event.nomination_title = entry.nomination_title
                    existing_event.order = order
                    await self.schedule_gateway.save_event(existing_event)
                    orphaned_events.remove(existing_event)
                    logger.info(
                        "Existing event was updated",
                        extra={"existing_event": existing_event},
                    )
                else:
                    # Create new event
                    new_event = ScheduleEvent(
                        public_number=entry.public_number,
                        title=entry.title,
                        duration=entry.duration,
                        block_title=entry.block_title,
                        nomination_title=entry.nomination_title,
                        order=order,
                        is_current=False,
                        is_skipped=False,
                    )
                    await self.schedule_gateway.add_event(new_event)
                    logger.info("New event was added", extra={"new_event": new_event})
                order += ORDER_STEP
            for e in orphaned_events:
                await self.schedule_gateway.delete_event(e)
                logger.info("Orphaned event was deleted", extra={"deleted_event": e})
            await self.uow.commit()
