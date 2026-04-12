import logging
from uuid import uuid7

from pydantic import BaseModel

from fanfan.application.interactors.common.current_user import get_current_user
from fanfan.application.interactors.schedule_mgmt.common import ANNOUNCE_LIMIT_NAME
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.rate_lock import RateLockFactory
from fanfan.application.ports.repositories.app_settings import AppSettingsRepository
from fanfan.application.ports.repositories.schedule_changes import (
    ScheduleChangeRepository,
)
from fanfan.application.ports.repositories.schedule_events import (
    ScheduleEventRepository,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.mailing import MailingService
from fanfan.application.services.permissions import PermissionService
from fanfan.core.events.schedule import CreatedScheduleChangeEvent
from fanfan.core.exceptions.limiter import RateLockCooldown
from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    EventNotFound,
    ScheduleEditTooFast,
)
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.permission import Permissions
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class UpdateScheduleEventSkipInput(BaseModel):
    event_id: ScheduleEventId
    is_skipped: bool


class UpdateScheduleEventSkip:
    def __init__(
        self,
        schedule_repo: ScheduleEventRepository,
        settings_repo: AppSettingsRepository,
        changes_repo: ScheduleChangeRepository,
        user_repo: UserRepository,
        perm_service: PermissionService,
        trx: TransactionManager,
        rate_lock_factory: RateLockFactory,
        id_provider: IdProvider,
        events_broker: EventBroker,
        notifications_service: MailingService,
    ) -> None:
        self.schedule_repo = schedule_repo
        self.settings_repo = settings_repo
        self.changes_repo = changes_repo
        self.user_repo = user_repo
        self.perm_service = perm_service
        self.trx = trx
        self.rate_lock_factory = rate_lock_factory
        self.events_broker = events_broker
        self.id_provider = id_provider
        self.notifications_service = notifications_service

    async def __call__(self, data: UpdateScheduleEventSkipInput) -> None:
        current_user = await get_current_user(
            id_provider=self.id_provider,
            user_repo=self.user_repo,
        )
        await self.perm_service.ensure(
            user=current_user, perm_name=Permissions.SCHEDULE_MANAGE
        )

        settings = await self.settings_repo.get()
        lock = self.rate_lock_factory(
            ANNOUNCE_LIMIT_NAME,
            cooldown_period=settings.limits.announcement_timeout,
        )

        try:
            async with lock:
                # Get and check event
                event = await self.schedule_repo.get_by_id(data.event_id)
                if event is None:
                    raise EventNotFound(event_id=data.event_id)
                if event.is_current:
                    raise CurrentEventNotAllowed

                # Get next event at this point
                next_event_before = await self.schedule_repo.get_next()

                # Toggle event skip
                event.is_skipped = not event.is_skipped
                await self.schedule_repo.save(event)

                next_event_after = await self.schedule_repo.get_next()

                # Save schedule change
                mailing = await self.notifications_service.create_new_mailing(
                    total_count=0, by_user_id=current_user.id
                )
                schedule_change = ScheduleChange(
                    id=ScheduleChangeId(uuid7()),
                    type=ScheduleChangeType.SKIPPED
                    if event.is_skipped
                    else ScheduleChangeType.UNSKIPPED,
                    changed_event_id=event.id,
                    argument_event_id=None,
                    mailing_id=mailing.id,
                    user_id=current_user.id,
                    send_global_announcement=(next_event_before != next_event_after),
                )
                await self.changes_repo.add(schedule_change)

                # Commit and proceed
                await self.trx.commit()
                await self.events_broker.publish(
                    CreatedScheduleChangeEvent(schedule_change_id=schedule_change.id)
                )

                # Update event after commit
                event = await self.schedule_repo.get_by_id(data.event_id)

                logger.info(
                    "Event %s was skipped by user %s",
                    data.event_id,
                    current_user.id,
                    extra={"skipped_event": event},
                )
                return
        except RateLockCooldown as e:
            raise ScheduleEditTooFast(
                announcement_timeout=e.limit_timeout, old_timestamp=e.current_timestamp
            ) from e
