import logging

from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.repositories.schedule_events import (
    ScheduleEventRepository,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.core.exceptions.base import AccessDenied
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


class ImportScheduleInput(BaseModel):
    schedule: list[ScheduleEntry]


class ImportSchedule:
    def __init__(
        self,
        schedule_repo: ScheduleEventRepository,
        trx: TransactionManager,
        id_provider: IdProvider,
        user_repo: UserRepository,
    ):
        self.user_repo = user_repo
        self.id_provider = id_provider
        self.trx = trx
        self.schedule_repo = schedule_repo

    async def __call__(self, data: ImportScheduleInput) -> None:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
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
                existing_event.title = entry.title
                existing_event.duration = entry.duration
                existing_event.block_title = entry.block_title
                existing_event.nomination_title = entry.nomination_title
                existing_event.order = order
                await self.schedule_repo.save(existing_event)
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
                await self.schedule_repo.add(new_event)
                logger.info("New event was added", extra={"new_event": new_event})
            order += ORDER_STEP
        for e in orphaned_events:
            await self.schedule_repo.delete(e)
            logger.info("Orphaned event was deleted", extra={"deleted_event": e})
        await self.trx.commit()
