import logging

from pydantic import BaseModel

from fanfan.application.interactors.schedule_mgmt.common import ANNOUNCE_LIMIT_NAME
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.rate_lock import RateLockFactory
from fanfan.application.ports.repositories.app_settings import AppSettingsRepository
from fanfan.application.ports.repositories.mailings import MailingRepository
from fanfan.application.ports.repositories.schedule_changes import (
    ScheduleChangeRepository,
)
from fanfan.application.ports.repositories.schedule_events import (
    ScheduleEventRepository,
)
from fanfan.application.ports.repositories.users import UserRepository
from fanfan.application.ports.trx import TransactionManager
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.rate_limit import RateLimitCooldown
from fanfan.core.exceptions.schedule import (
    EventNotFound,
    ScheduleEditTooFast,
)
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.permission import Permissions
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
        current_user_provider: CurrentUserProvider,
        events_broker: EventBroker,
        mailing_repo: MailingRepository,
    ) -> None:
        self.schedule_repo = schedule_repo
        self.settings_repo = settings_repo
        self.user_repo = user_repo
        self.perm_service = perm_service
        self.uow = trx
        self.rate_lock_factory = rate_lock_factory
        self.events_broker = events_broker
        self.current_user_provider = current_user_provider
        self.mailing_repo = mailing_repo
        self.changes_repo = changes_repo

    async def __call__(self, data: SetCurrentScheduleEventInput) -> None:
        current_user = await self.current_user_provider.require_user()
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
                    previous_current_event.unset_current()
                    await self.schedule_repo.save(previous_current_event)

                # Get event and set as current
                if data.event_id is not None:
                    event = await self.schedule_repo.get_by_id(data.event_id)
                    if event is None:
                        raise EventNotFound
                    event.set_current()
                    await self.schedule_repo.save(event)
                else:
                    event = None

                # Save schedule change
                mailing = Mailing.create(by_user_id=current_user.id)
                await self.mailing_repo.add(mailing)
                schedule_change = ScheduleChange.set_as_current(
                    changed_event_id=event.id if event else None,
                    previous_event_id=previous_current_event.id
                    if previous_current_event
                    else None,
                    mailing_id=mailing.id,
                    user_id=current_user.id,
                )
                await self.changes_repo.add(schedule_change)

                # Commit and proceed
                await self.uow.commit()
                for event in schedule_change.pull_events():
                    await self.events_broker.publish(event)

                logger.info(
                    "Event %s was set as current by user %s",
                    data.event_id,
                    current_user.id,
                    extra={"current_event": event},
                )
                return
        except RateLimitCooldown as e:
            raise ScheduleEditTooFast(
                retry_after=e.details["retry_after"],
            ) from e
