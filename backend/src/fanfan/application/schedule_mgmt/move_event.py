import logging

from pydantic import BaseModel

from fanfan.adapters.db.gateways.app_settings import SettingsGateway
from fanfan.adapters.db.gateways.schedule_changes import ScheduleChangeGateway
from fanfan.adapters.db.gateways.schedule_events import ScheduleEventGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.adapters.redis.rate_lock import RateLockFactory
from fanfan.application.common.id_provider import IdProvider
from fanfan.application.schedule_mgmt.common import (
    ANNOUNCE_LIMIT_NAME,
)
from fanfan.core.dto.schedule import ScheduleEventFullDTO
from fanfan.core.events.schedule import CreatedScheduleChangeEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.limiter import RateLockCooldown
from fanfan.core.exceptions.schedule import (
    EventNotFound,
    SameEventsAreNotAllowed,
    ScheduleEditTooFast,
)
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.schedule_change import (
    ScheduleChange,
)
from fanfan.core.services.notifications import NotificationService
from fanfan.core.services.perm import PermService
from fanfan.core.vo.permission import Permissions
from fanfan.core.vo.schedule_change import ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class MoveScheduleEventCommand(BaseModel):
    event_id: ScheduleEventId
    place_after_event_id: ScheduleEventId


class MoveScheduleEventResult(BaseModel):
    event: ScheduleEventFullDTO
    place_after_event: ScheduleEventFullDTO


class MoveScheduleEvent:
    def __init__(
        self,
        schedule_gateway: ScheduleEventGateway,
        user_gateway: UserGateway,
        notifications_service: NotificationService,
        settings_gateway: SettingsGateway,
        changes_gateway: ScheduleChangeGateway,
        perm_service: PermService,
        uow: UnitOfWork,
        id_provider: IdProvider,
        rate_lock_factory: RateLockFactory,
        events_broker: EventBroker,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.user_gateway = user_gateway
        self.notifications_service = notifications_service
        self.settings_gateway = settings_gateway
        self.changes_gateway = changes_gateway
        self.perm_service = perm_service
        self.uow = uow
        self.id_provider = id_provider
        self.rate_lock_factory = rate_lock_factory
        self.events_broker = events_broker

    async def __call__(self, data: MoveScheduleEventCommand) -> MoveScheduleEventResult:
        async with self.uow:
            current_user_id = await self.id_provider.get_current_user_id()
            if current_user_id is None:
                raise UserNotAuthenticated
            current_user = await self.user_gateway.get_user_by_id(current_user_id)
            if current_user is None:
                raise UserNotFound
            await self.perm_service.ensure(
                user=current_user, perm_name=Permissions.SCHEDULE_MANAGE
            )

            settings = await self.settings_gateway.get_settings()
            lock = self.rate_lock_factory(
                ANNOUNCE_LIMIT_NAME,
                cooldown_period=settings.limits.announcement_timeout,
            )

            try:
                async with lock:
                    # Get and check events
                    if data.event_id == data.place_after_event_id:
                        raise SameEventsAreNotAllowed
                    event = await self.schedule_gateway.get_event_by_id(data.event_id)
                    if event is None:
                        raise EventNotFound(event_id=data.event_id)

                    place_after_event = await self.schedule_gateway.read_event_by_id(
                        data.place_after_event_id
                    )
                    if place_after_event is None:
                        raise EventNotFound(event_id=data.place_after_event_id)
                    place_before_event = await self.schedule_gateway.get_next_by_order(
                        place_after_event.order
                    )
                    previous_event = await self.schedule_gateway.get_previous_by_order(
                        event.order
                    )

                    next_event_before_change = (
                        await self.schedule_gateway.read_next_event()
                    )

                    # Update event order
                    if place_before_event:
                        new_order = (
                            place_after_event.order + place_before_event.order
                        ) / 2
                    else:
                        new_order = place_after_event.order + 1

                    event.order = new_order
                    event = await self.schedule_gateway.save_event(event)

                    next_event_after_change = (
                        await self.schedule_gateway.read_next_event()
                    )

                    # Save schedule change
                    mailing = await self.notifications_service.create_new_mailing(
                        total_count=0, by_user_id=current_user.id
                    )
                    schedule_change = ScheduleChange(
                        type=ScheduleChangeType.MOVED,
                        changed_event_id=event.id,
                        argument_event_id=previous_event.id if previous_event else None,
                        mailing_id=mailing.id,
                        user_id=current_user.id,
                        send_global_announcement=(
                            next_event_before_change != next_event_after_change
                        ),
                    )
                    await self.changes_gateway.add_schedule_change(schedule_change)

                    # Commit and proceed
                    await self.uow.commit()
                    await self.events_broker.publish(
                        CreatedScheduleChangeEvent(
                            schedule_change_id=schedule_change.id
                        )
                    )

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
                    return MoveScheduleEventResult(
                        event=await self.schedule_gateway.read_event_by_id(event.id),
                        place_after_event=place_after_event,
                    )
            except RateLockCooldown as e:
                raise ScheduleEditTooFast(
                    announcement_timeout=e.limit_timeout,
                    old_timestamp=e.current_timestamp,
                ) from e
