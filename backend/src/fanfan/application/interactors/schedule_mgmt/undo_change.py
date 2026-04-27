import logging

from pydantic import BaseModel

from fanfan.application.ports.events_broker import EventBroker
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
from fanfan.core.events.schedule import UndoScheduleChangeEvent
from fanfan.core.exceptions.schedule import (
    OutdatedScheduleChange,
    ScheduleChangeNotFound,
)
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.vo.permission import Permissions
from fanfan.core.vo.schedule_change import ScheduleChangeId, ScheduleChangeType

logger = logging.getLogger(__name__)


class UndoScheduleChangeInput(BaseModel):
    schedule_change_id: ScheduleChangeId


class UndoScheduleChange:
    def __init__(
        self,
        trx: TransactionManager,
        changes_repo: ScheduleChangeRepository,
        user_repo: UserRepository,
        schedule_repo: ScheduleEventRepository,
        events_broker: EventBroker,
        current_user_provider: CurrentUserProvider,
        perm_service: PermissionService,
    ):
        self.trx = trx
        self.changes_repo = changes_repo
        self.schedule_repo = schedule_repo
        self.user_repo = user_repo
        self.events_broker = events_broker
        self.current_user_provider = current_user_provider
        self.perm_service = perm_service

    async def _handle_set_as_current(
        self,
        changed_event: ScheduleEvent | None,
        previous_event: ScheduleEvent | None,
    ) -> None:
        current_event = await self.schedule_repo.get_current()

        if changed_event != current_event:
            raise OutdatedScheduleChange

        if changed_event:
            changed_event.is_current = False
            await self.schedule_repo.save(changed_event)

        if previous_event:
            previous_event.is_current = True
            await self.schedule_repo.save(previous_event)

    async def _handle_moved(
        self,
        changed_event: ScheduleEvent,
        place_after_event: ScheduleEvent | None,
    ) -> None:
        if place_after_event:
            place_before_event = await self.schedule_repo.get_next_by_order(
                place_after_event.order
            )
            if place_before_event:
                new_order = (place_after_event.order + place_before_event.order) / 2
            else:
                new_order = place_after_event.order + 1
        else:
            first_event = await self.schedule_repo.get_by_queue(1)
            new_order = first_event.order - 1 if first_event else 1

        changed_event.order = new_order
        await self.schedule_repo.save(changed_event)

    async def __call__(self, data: UndoScheduleChangeInput) -> None:
        current_user = await self.current_user_provider.require_user()
        await self.perm_service.ensure(
            user=current_user, perm_name=Permissions.SCHEDULE_MANAGE
        )
        schedule_change = await self.changes_repo.get_by_id(data.schedule_change_id)
        if schedule_change is None:
            raise ScheduleChangeNotFound

        # TODO check for None
        changed_event = (
            await self.schedule_repo.get_by_id(schedule_change.changed_event_id)
            if schedule_change.changed_event_id
            else None
        )
        argument_event = (
            await self.schedule_repo.get_by_id(schedule_change.argument_event_id)
            if schedule_change.argument_event_id
            else None
        )

        if schedule_change.type is ScheduleChangeType.SET_AS_CURRENT:
            await self._handle_set_as_current(changed_event, argument_event)

        if schedule_change.type is ScheduleChangeType.MOVED and changed_event:
            await self._handle_moved(changed_event, argument_event)

        if schedule_change.type is ScheduleChangeType.SKIPPED and changed_event:
            changed_event.is_skipped = False
            await self.schedule_repo.save(changed_event)

        if schedule_change.type is ScheduleChangeType.UNSKIPPED and changed_event:
            changed_event.is_skipped = True
            await self.schedule_repo.save(changed_event)

        await self.changes_repo.delete(schedule_change)
        await self.trx.commit()

        await self.events_broker.publish(
            UndoScheduleChangeEvent(mailing_id=schedule_change.mailing_id)
        )

        logger.info(
            "User %s reverted schedule change %s",
            current_user.id,
            data.schedule_change_id,
        )
