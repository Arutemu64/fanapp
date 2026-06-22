import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.ports.gateways.schedule_events import (
    ScheduleEventGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.schedule import (
    EventNotFound,
    OutdatedScheduleChange,
    ScheduleChangeNotFound,
)
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.vo.permission import PermissionName, Permissions
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType
from fanfan.core.vo.schedule_event import ScheduleEventId

logger = logging.getLogger(__name__)


class UndoScheduleChangeInput(BaseModel):
    schedule_change_id: ScheduleChangeId


class UndoScheduleChange:
    def __init__(
        self,
        uow: UnitOfWork,
        changes_gateway: ScheduleChangeGateway,
        user_gateway: UserGateway,
        schedule_gateway: ScheduleEventGateway,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ):
        self.uow = uow
        self.changes_gateway = changes_gateway
        self.schedule_gateway = schedule_gateway
        self.user_gateway = user_gateway
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def _handle_set_as_current(
        self,
        changed_event: ScheduleEvent | None,
        previous_event: ScheduleEvent | None,
    ) -> None:
        current_event = await self.schedule_gateway.get_current()

        if changed_event != current_event:
            raise OutdatedScheduleChange

        if changed_event:
            changed_event.unset_current()
            await self.schedule_gateway.save(changed_event)

        if previous_event:
            previous_event.set_current()
            await self.schedule_gateway.save(previous_event)

    async def _handle_moved(
        self,
        changed_event: ScheduleEvent,
        place_after_event: ScheduleEvent | None,
    ) -> None:
        if place_after_event:
            place_before_event = await self.schedule_gateway.get_next_by_order(
                place_after_event.order
            )
            if place_before_event:
                changed_event.place_after(place_after_event, place_before_event)
            else:
                changed_event.place_after(place_after_event, None)
        else:
            first_event = await self.schedule_gateway.get_by_queue(1)
            changed_event.place_before_first(first_event)

        await self.schedule_gateway.save(changed_event)

    async def _require_event(
        self, event_id: ScheduleEventId | None
    ) -> ScheduleEvent | None:
        # A null id means the change simply had no event in that slot. A non-null
        # id that resolves to nothing is an inconsistent state, so fail loud
        # instead of silently skipping the revert below.
        if event_id is None:
            return None
        event = await self.schedule_gateway.get_by_id(event_id)
        if event is None:
            raise EventNotFound
        return event

    async def __call__(self, data: UndoScheduleChangeInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, perm_name=PermissionName(Permissions.SCHEDULE_MANAGE)
        )
        schedule_change = await self.changes_gateway.get_by_id(data.schedule_change_id)
        if schedule_change is None:
            raise ScheduleChangeNotFound

        changed_event = await self._require_event(schedule_change.changed_event_id)
        argument_event = await self._require_event(schedule_change.argument_event_id)

        if schedule_change.type is ScheduleChangeType.SET_AS_CURRENT:
            await self._handle_set_as_current(changed_event, argument_event)

        if schedule_change.type is ScheduleChangeType.MOVED and changed_event:
            await self._handle_moved(changed_event, argument_event)

        if schedule_change.type is ScheduleChangeType.SKIPPED and changed_event:
            changed_event.unskip()
            await self.schedule_gateway.save(changed_event)

        if schedule_change.type is ScheduleChangeType.UNSKIPPED and changed_event:
            changed_event.skip()
            await self.schedule_gateway.save(changed_event)

        schedule_change.mark_undone()
        await self.changes_gateway.delete(schedule_change)
        await self.uow.commit()

        logger.info(
            "Schedule change reverted",
            extra={
                "schedule_change_id": str(data.schedule_change_id),
                "actor_id": str(current_user.id),
            },
        )
