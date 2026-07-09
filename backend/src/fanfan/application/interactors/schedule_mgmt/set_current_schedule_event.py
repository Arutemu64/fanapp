import logging
from datetime import UTC, datetime

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


class SetCurrentScheduleEventInput(BaseModel):
    event_id: ScheduleEventId | None


class SetCurrentScheduleEvent:
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
        self.user_gateway = user_gateway
        self.perm_service = perm_service
        self.uow = uow
        self.rate_lock_factory = rate_lock_factory
        self.current_user_provider = current_user_provider
        self.mailing_gateway = mailing_gateway
        self.changes_gateway = changes_gateway

    async def __call__(self, data: SetCurrentScheduleEventInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, perm_name=PermissionName(Permissions.SCHEDULE_MANAGE)
        )

        settings = await self.settings_gateway.get()
        lock = self.rate_lock_factory(
            ANNOUNCE_LIMIT_NAME,
            cooldown_period=settings.limits.announcement_timeout,
        )

        try:
            async with lock:
                previous_current_event = await self.schedule_gateway.get_current()
                if previous_current_event:
                    previous_current_event.unset_current()
                    await self.schedule_gateway.save(previous_current_event)

                if data.event_id is not None:
                    event = await self.schedule_gateway.get_by_id(data.event_id)
                    if event is None:
                        raise EventNotFound
                    event.set_current(now=datetime.now(UTC))
                    await self.schedule_gateway.save(event)
                else:
                    event = None

                mailing = Mailing.create(by_user_id=current_user.id)
                await self.mailing_gateway.add(mailing)
                schedule_change = ScheduleChange.set_as_current(
                    changed_event_id=event.id if event else None,
                    previous_event_id=previous_current_event.id
                    if previous_current_event
                    else None,
                    mailing_id=mailing.id,
                    user_id=current_user.id,
                )
                await self.changes_gateway.add(schedule_change)

                await self.uow.commit()

                logger.info(
                    "Schedule event set as current",
                    extra={
                        "event_id": str(data.event_id) if data.event_id else None,
                        "actor_id": str(current_user.id),
                    },
                )
                return
        except RateLimitCooldown as e:
            raise ScheduleEditTooFast(
                retry_after=e.details["retry_after"],
            ) from e
