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
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class UpdateScheduleEventSkipInput(BaseModel):
    event_id: ScheduleEventId
    is_skipped: bool


class UpdateScheduleEventSkip:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        settings_gateway: AppSettingsGateway,
        changes_gateway: ScheduleChangeGateway,
        user_gateway: UserGateway,
        perm_service: PermissionService,
        uow: UnitOfWork,
        rate_lock_factory: RateLockFactory,
        current_user_provider: CurrentUserProvider,
        mailing_gateway: MailingGateway,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.settings_gateway = settings_gateway
        self.changes_gateway = changes_gateway
        self.user_gateway = user_gateway
        self.perm_service = perm_service
        self.uow = uow
        self.rate_lock_factory = rate_lock_factory
        self.current_user_provider = current_user_provider
        self.mailing_gateway = mailing_gateway

    async def __call__(self, data: UpdateScheduleEventSkipInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, permission=Permission.SCHEDULE_MANAGE
        )

        settings = await self.settings_gateway.get()
        lock = self.rate_lock_factory(
            ANNOUNCE_LIMIT_NAME,
            cooldown_period=settings.limits.announcement_timeout_seconds,
        )

        try:
            async with lock:
                event = await self.schedule_gateway.get_by_id(data.event_id)
                if event is None:
                    raise EventNotFound

                # Snapshot the next event before and after the change so the
                # mailing can tell subscribers whether their next event moved.
                next_event_before = await self.schedule_gateway.get_next()

                if data.is_skipped:
                    event.skip()
                else:
                    event.unskip()
                await self.schedule_gateway.save(event)

                next_event_after = await self.schedule_gateway.get_next()

                mailing = Mailing.create(by_user_id=current_user.id)
                await self.mailing_gateway.add(mailing)
                factory = ScheduleChange.skipped
                if not event.is_skipped:
                    factory = ScheduleChange.unskipped
                schedule_change = factory(
                    event_id=event.id,
                    mailing_id=mailing.id,
                    user_id=current_user.id,
                    next_event_changed=(next_event_before != next_event_after),
                )
                await self.changes_gateway.add(schedule_change)

                await self.uow.commit()

                # Re-read so the logged event carries its post-commit state.
                event = await self.schedule_gateway.get_by_id(data.event_id)

                logger.info(
                    "Schedule event skip updated",
                    extra={
                        "event_id": str(data.event_id),
                        "is_skipped": data.is_skipped,
                        "actor_id": str(current_user.id),
                    },
                )
                return
        except RateLimitCooldown as e:
            raise ScheduleEditTooFast(
                retry_after=e.details["retry_after"],
            ) from e
