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
    EventNotFound,
    ScheduleEditTooFast,
    SkippedEventNotAllowed,
)
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.permission import Permissions
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class SetCurrentScheduleEventInput(BaseModel):
    event_id: ScheduleEventId | None


class SetCurrentScheduleEvent:
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
        self.user_repo = user_repo
        self.perm_service = perm_service
        self.uow = trx
        self.rate_lock_factory = rate_lock_factory
        self.events_broker = events_broker
        self.id_provider = id_provider
        self.notifications_service = notifications_service
        self.changes_repo = changes_repo

    async def __call__(self, data: SetCurrentScheduleEventInput) -> None:
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
                # Unset current event
                previous_current_event = await self.schedule_repo.get_current()
                if previous_current_event:
                    previous_current_event.is_current = False
                    await self.schedule_repo.save(previous_current_event)

                # Get event and set as current
                if data.event_id is not None:
                    event = await self.schedule_repo.get_by_id(data.event_id)
                    if event is None:
                        raise EventNotFound(data.event_id)
                    if event.is_skipped:
                        raise SkippedEventNotAllowed
                    event.is_current = True
                    await self.schedule_repo.save(event)
                else:
                    event = None

                # Save schedule change
                mailing = await self.notifications_service.create_new_mailing(
                    total_count=0, by_user_id=current_user.id
                )
                schedule_change = ScheduleChange(
                    id=ScheduleChangeId(uuid7()),
                    type=ScheduleChangeType.SET_AS_CURRENT,
                    changed_event_id=event.id if event else None,
                    argument_event_id=previous_current_event.id
                    if previous_current_event
                    else None,
                    mailing_id=mailing.id,
                    user_id=current_user.id,
                    send_global_announcement=True,
                )
                await self.changes_repo.add(schedule_change)

                # Commit and proceed
                await self.uow.commit()
                await self.events_broker.publish(
                    CreatedScheduleChangeEvent(schedule_change_id=schedule_change.id)
                )

                logger.info(
                    "Event %s was set as current by user %s",
                    data.event_id,
                    current_user.id,
                    extra={"current_event": event},
                )
                return
        except RateLockCooldown as e:
            raise ScheduleEditTooFast(
                announcement_timeout=e.limit_timeout,
                old_timestamp=e.current_timestamp,
            ) from e
