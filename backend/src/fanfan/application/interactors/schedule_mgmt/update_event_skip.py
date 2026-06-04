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
from fanfan.core.exceptions.rate_limit import RateLockCooldown
from fanfan.core.exceptions.schedule import (
    EventNotFound,
    ScheduleEditTooFast,
)
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.permission import Permissions
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
        current_user_provider: CurrentUserProvider,
        events_broker: EventBroker,
        mailing_repo: MailingRepository,
    ) -> None:
        self.schedule_repo = schedule_repo
        self.settings_repo = settings_repo
        self.changes_repo = changes_repo
        self.user_repo = user_repo
        self.perm_service = perm_service
        self.trx = trx
        self.rate_lock_factory = rate_lock_factory
        self.events_broker = events_broker
        self.current_user_provider = current_user_provider
        self.mailing_repo = mailing_repo

    async def __call__(self, data: UpdateScheduleEventSkipInput) -> None:
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
                # Get and check event
                event = await self.schedule_repo.get_by_id(data.event_id)
                if event is None:
                    raise EventNotFound

                # Get next event at this point
                next_event_before = await self.schedule_repo.get_next()

                # Update event skip state through domain methods.
                if data.is_skipped:
                    event.skip()
                else:
                    event.unskip()
                await self.schedule_repo.save(event)

                next_event_after = await self.schedule_repo.get_next()

                # Save schedule change
                mailing = Mailing.create(by_user_id=current_user.id)
                await self.mailing_repo.add(mailing)
                factory = ScheduleChange.skipped
                if not event.is_skipped:
                    factory = ScheduleChange.unskipped
                schedule_change = factory(
                    event_id=event.id,
                    mailing_id=mailing.id,
                    user_id=current_user.id,
                    next_event_changed=(next_event_before != next_event_after),
                )
                await self.changes_repo.add(schedule_change)

                # Commit and proceed
                await self.trx.commit()
                for event in schedule_change.pull_events():
                    await self.events_broker.publish(event)

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
                retry_after=e.details["retry_after"],
            ) from e
