import logging

from pydantic import BaseModel

from fanfan.application.ports.repositories.schedule_events import (
    ScheduleEventRepository,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.vo.schedule_event import (
    ScheduleEventPublicNumber,
    generate_schedule_event_id,
)
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


class ImportScheduleInput(BaseModel):
    schedule: list[ScheduleEntry]


class ImportSchedule:
    def __init__(
        self,
        schedule_repo: ScheduleEventRepository,
        trx: TransactionManager,
        current_user_provider: CurrentUserProvider,
        user_repo: UserRepository,
    ):
        self.user_repo = user_repo
        self.current_user_provider = current_user_provider
        self.trx = trx
        self.schedule_repo = schedule_repo

    async def __call__(self, data: ImportScheduleInput) -> None:
        current_user = await self.current_user_provider.require_user()
        if current_user.role is not UserRole.ORG:
            raise AccessDenied
        orphaned_events = await self.schedule_repo.list_all()
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
                await self.schedule_repo.save(existing_event)
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
                await self.schedule_repo.add(new_event)
                logger.info("New event was added", extra={"new_event": new_event})
            order += ORDER_STEP
        for e in orphaned_events:
            await self.schedule_repo.delete(e)
            logger.info("Orphaned event was deleted", extra={"deleted_event": e})
        await self.trx.commit()
