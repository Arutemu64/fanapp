import logging
from uuid import uuid7

from pydantic import BaseModel

from fanfan.adapters.db.gateways.app_settings import SettingsGateway
from fanfan.adapters.db.gateways.schedule_changes import ScheduleChangeGateway
from fanfan.adapters.db.gateways.schedule_events import ScheduleEventGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.adapters.redis.rate_lock import RateLockFactory
from fanfan.application.common.id_provider import IdProvider
from fanfan.application.schedule_mgmt.common import ANNOUNCE_LIMIT_NAME
from fanfan.core.constants.permissions import Permissions
from fanfan.core.dto.schedule import ScheduleEventFullDTO
from fanfan.core.events.schedule import CreatedScheduleChangeEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.limiter import RateLockCooldown
from fanfan.core.exceptions.schedule import (
    EventNotFound,
    ScheduleEditTooFast,
    SkippedEventNotAllowed,
)
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.services.notifications import NotificationService
from fanfan.core.services.perm import PermService
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class SetCurrentScheduleEventCommand(BaseModel):
    event_id: ScheduleEventId | None


class SetCurrentScheduleEventResult(BaseModel):
    current_event: ScheduleEventFullDTO | None
    schedule_change_id: ScheduleChangeId


class SetCurrentScheduleEvent:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        settings_gateway: SettingsGateway,
        changes_gateway: ScheduleChangeGateway,
        user_gateway: UserGateway,
        perm_service: PermService,
        uow: UnitOfWork,
        rate_lock_factory: RateLockFactory,
        id_provider: IdProvider,
        events_broker: EventBroker,
        notifications_service: NotificationService,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.settings_gateway = settings_gateway
        self.user_gateway = user_gateway
        self.perm_service = perm_service
        self.uow = uow
        self.rate_lock_factory = rate_lock_factory
        self.events_broker = events_broker
        self.id_provider = id_provider
        self.notifications_service = notifications_service
        self.changes_gateway = changes_gateway

    async def __call__(
        self, data: SetCurrentScheduleEventCommand
    ) -> SetCurrentScheduleEventResult:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            await self.perm_service.ensure(
                user=current_user, perm_name=Permissions.CAN_MANAGE_SCHEDULE
            )

            settings = await self.settings_gateway.get_settings()
            lock = self.rate_lock_factory(
                ANNOUNCE_LIMIT_NAME,
                cooldown_period=settings.limits.announcement_timeout,
            )

            try:
                async with lock:
                    # Unset current event
                    previous_current_event = (
                        await self.schedule_gateway.get_current_event()
                    )
                    if previous_current_event:
                        previous_current_event.is_current = False
                        await self.schedule_gateway.save_event(previous_current_event)

                    # Get event and set as current
                    if data.event_id is not None:
                        event = await self.schedule_gateway.get_event_by_id(
                            data.event_id
                        )
                        if event is None:
                            raise EventNotFound(data.event_id)
                        if event.is_skipped:
                            raise SkippedEventNotAllowed
                        event.is_current = True
                        await self.schedule_gateway.save_event(event)
                    else:
                        event = None

                    # Save schedule change
                    mailing = await self.notifications_service.create_new_mailing(
                        total_notifications=0, by_user_id=current_user.id
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
                    schedule_change = await self.changes_gateway.add_schedule_change(
                        schedule_change
                    )

                    # Commit and proceed
                    await self.uow.commit()
                    await self.events_broker.publish(
                        CreatedScheduleChangeEvent(
                            schedule_change_id=schedule_change.id
                        )
                    )

                    logger.info(
                        "Event %s was set as current by user %s",
                        data.event_id,
                        current_user.id,
                        extra={"current_event": event},
                    )
                    return SetCurrentScheduleEventResult(
                        current_event=await self.schedule_gateway.read_event_by_id(
                            event.id
                        )
                        if event
                        else None,
                        schedule_change_id=schedule_change.id,
                    )
            except RateLockCooldown as e:
                raise ScheduleEditTooFast(
                    announcement_timeout=e.limit_timeout,
                    old_timestamp=e.current_timestamp,
                ) from e
