import logging

from pydantic import BaseModel

from fanfan.application.interactors.schedule_mgmt.common import (
    ANNOUNCE_LIMIT_NAME,
)
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
from fanfan.core.models.schedule_change import (
    ScheduleChange,
)
from fanfan.core.vo.permission import PermissionName, Permissions
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class MoveScheduleEventInput(BaseModel):
    event_id: ScheduleEventId
    place_after_event_id: ScheduleEventId


class MoveScheduleEvent:
    def __init__(
        self,
        schedule_repo: ScheduleEventRepository,
        user_repo: UserRepository,
        mailing_repo: MailingRepository,
        settings_repo: AppSettingsRepository,
        changes_repo: ScheduleChangeRepository,
        perm_service: PermissionService,
        trx: TransactionManager,
        current_user_provider: CurrentUserProvider,
        rate_lock_factory: RateLockFactory,
        events_broker: EventBroker,
    ) -> None:
        self.schedule_repo = schedule_repo
        self.user_repo = user_repo
        self.mailing_repo = mailing_repo
        self.settings_repo = settings_repo
        self.changes_repo = changes_repo
        self.perm_service = perm_service
        self.trx = trx
        self.current_user_provider = current_user_provider
        self.rate_lock_factory = rate_lock_factory
        self.events_broker = events_broker

    async def __call__(self, data: MoveScheduleEventInput) -> None:
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
                # Get and check events
                event = await self.schedule_repo.get_by_id(data.event_id)
                if event is None:
                    raise EventNotFound

                place_after_event = await self.schedule_repo.get_by_id(
                    data.place_after_event_id
                )
                if place_after_event is None:
                    raise EventNotFound
                place_before_event = await self.schedule_repo.get_next_by_order(
                    place_after_event.order
                )
                previous_event = await self.schedule_repo.get_previous_by_order(
                    event.order
                )

                next_event_before_change = await self.schedule_repo.get_next()

                # Update event order through the domain model.
                event.place_after(place_after_event, place_before_event)
                await self.schedule_repo.save(event)

                next_event_after_change = await self.schedule_repo.get_next()

                # Save schedule change
                mailing = Mailing.create(by_user_id=current_user.id)
                await self.mailing_repo.add(mailing)
                schedule_change = ScheduleChange.moved(
                    event_id=event.id,
                    previous_event_id=previous_event.id if previous_event else None,
                    mailing_id=mailing.id,
                    user_id=current_user.id,
                    next_event_changed=(
                        next_event_before_change != next_event_after_change
                    ),
                )
                await self.changes_repo.add(schedule_change)

                # Commit and proceed
                await self.trx.commit()
                for event in schedule_change.pull_events():
                    await self.events_broker.publish(event)

                logger.info(
                    "Event %s was placed after event %s by user %s",
                    data.event_id,
                    data.place_after_event_id,
                    current_user.id,
                    extra={
                        "moved_event": event,
                        "place_after_event": place_after_event,
                    },
                )
                return
        except RateLimitCooldown as e:
            raise ScheduleEditTooFast(
                retry_after=e.details["retry_after"],
            ) from e
