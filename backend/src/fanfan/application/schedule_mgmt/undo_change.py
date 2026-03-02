import logging

from pydantic import BaseModel

from fanfan.adapters.db.gateways.schedule_changes import ScheduleChangeGateway
from fanfan.adapters.db.gateways.schedule_events import ScheduleEventGateway
from fanfan.adapters.db.gateways.users import UserGateway
from fanfan.adapters.db.uow import UnitOfWork
from fanfan.adapters.nats.events_broker import EventBroker
from fanfan.application.common.id_provider import IdProvider
from fanfan.core.constants.permissions import Permissions
from fanfan.core.events.schedule import UndoScheduleChangeEvent
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.schedule import (
    OutdatedScheduleChange,
    ScheduleChangeNotFound,
)
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.services.perm import PermService
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType

logger = logging.getLogger(__name__)


class UndoScheduleChangeCommand(BaseModel):
    schedule_change_id: ScheduleChangeId


class UndoScheduleChange:
    def __init__(
        self,
        uow: UnitOfWork,
        schedule_change_gateway: ScheduleChangeGateway,
        user_gateway: UserGateway,
        schedule_gateway: ScheduleEventGateway,
        events_broker: EventBroker,
        id_provider: IdProvider,
        perm_service: PermService,
    ):
        self.uow = uow
        self.schedule_change_gateway = schedule_change_gateway
        self.schedule_gateway = schedule_gateway
        self.user_gateway = user_gateway
        self.events_broker = events_broker
        self.id_provider = id_provider
        self.perm_service = perm_service

    async def __call__(self, data: UndoScheduleChangeCommand) -> None:  # noqa: C901
        current_user_id = await self.id_provider.get_current_user_id()
        if current_user_id is None:
            raise UserNotAuthenticated
        current_user = await self.user_gateway.get_user_by_id(current_user_id)
        if current_user is None:
            raise UserNotFound
        await self.perm_service.ensure(
            user=current_user, perm_name=Permissions.CAN_MANAGE_SCHEDULE
        )
        schedule_change = await self.schedule_change_gateway.get_schedule_change(
            data.schedule_change_id
        )
        if schedule_change is None:
            raise ScheduleChangeNotFound

        changed_event = await self.schedule_gateway.get_event_by_id(
            schedule_change.changed_event_id
        )
        argument_event = await self.schedule_gateway.get_event_by_id(
            schedule_change.argument_event_id
        )

        async with self.uow:
            if schedule_change.type is ScheduleChangeType.SET_AS_CURRENT:
                previous_event = argument_event
                current_event = await self.schedule_gateway.get_current_event()

                if changed_event != current_event:
                    raise OutdatedScheduleChange

                if changed_event:
                    changed_event.is_current = False
                    await self.schedule_gateway.save_event(changed_event)

                if previous_event:
                    previous_event.is_current = True
                    await self.schedule_gateway.save_event(previous_event)

            if schedule_change.type is ScheduleChangeType.MOVED:
                place_after_event = argument_event

                if place_after_event:
                    place_before_event = await self.schedule_gateway.get_next_by_order(
                        place_after_event.order
                    )
                    if place_before_event:
                        new_order = (
                            place_after_event.order + place_before_event.order
                        ) / 2
                    else:
                        new_order = place_after_event.order + 1
                else:
                    first_event = await self.schedule_gateway.read_event_by_queue(1)
                    new_order = first_event.order - 1 if first_event else 1

                changed_event.order = new_order
                await self.schedule_gateway.save_event(changed_event)

            if schedule_change.type is ScheduleChangeType.SKIPPED:
                changed_event.is_skipped = False
                await self.schedule_gateway.save_event(changed_event)

            if schedule_change.type is ScheduleChangeType.UNSKIPPED:
                changed_event.is_skipped = True
                await self.schedule_gateway.save_event(changed_event)

            await self.schedule_change_gateway.delete_schedule_change(schedule_change)
            await self.uow.commit()

            await self.events_broker.publish(
                UndoScheduleChangeEvent(mailing_id=schedule_change.mailing_id)
            )

            logger.info(
                "User %s reverted schedule change %s",
                current_user.id,
                data.schedule_change_id,
                extra={"schedule_change": schedule_change},
            )
