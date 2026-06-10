import logging

from pydantic import BaseModel

from fanfan.application.interactors.schedule_mgmt.common import ANNOUNCE_LIMIT_NAME
from fanfan.application.ports.gateways.app_settings import AppSettingsGateway
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.ports.gateways.schedule_events import (
    ScheduleEventGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.rate_lock import RateLockFactory
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.rate_limit import RateLimitCooldown
from fanfan.core.exceptions.schedule import (
    EventNotFound,
    ScheduleEditTooFast,
)
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.vo.permission import PermissionName, Permissions
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class UpdateScheduleEventSkipInput(BaseModel):
    event_id: ScheduleEventId
    is_skipped: bool


class UpdateScheduleEventSkip:
    def __init__(
        self,
        schedule_repo: ScheduleEventGateway,
        settings_repo: AppSettingsGateway,
        changes_repo: ScheduleChangeGateway,
        user_repo: UserGateway,
        perm_service: PermissionService,
        uow: UnitOfWork,
        rate_lock_factory: RateLockFactory,
        current_user_provider: CurrentUserProvider,
        mailing_repo: MailingGateway,
    ) -> None:
        self.schedule_repo = schedule_repo
        self.settings_repo = settings_repo
        self.changes_repo = changes_repo
        self.user_repo = user_repo
        self.perm_service = perm_service
        self.uow = uow
        self.rate_lock_factory = rate_lock_factory
        self.current_user_provider = current_user_provider
        self.mailing_repo = mailing_repo

    async def __call__(self, data: UpdateScheduleEventSkipInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, perm_name=PermissionName(Permissions.SCHEDULE_MANAGE)
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
                await self.uow.commit()

                # Update event after commit
                event = await self.schedule_repo.get_by_id(data.event_id)

                logger.info(
                    "Event %s was skipped by user %s",
                    data.event_id,
                    current_user.id,
                    extra={"skipped_event": event},
                )
                return
        except RateLimitCooldown as e:
            raise ScheduleEditTooFast(
                retry_after=e.details["retry_after"],
            ) from e
