import enum
import logging

from pydantic import BaseModel

from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.permissions import PermissionService
from fanfan.application.services.schedule_operations import ScheduleOperations
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_change import ScheduleChangeType
from fanfan.core.vo.user import STAGE_CONSOLE_USER_ID

logger = logging.getLogger(__name__)


class StageConsoleAction(enum.StrEnum):
    SET_CURRENT = "set_current"
    SKIP = "skip"
    UNSKIP = "unskip"
    MOVE = "move"
    UNMOVE = "unmove"


class ApplyStageConsoleActionInput(BaseModel):
    action: StageConsoleAction
    number: int
    # MOVE: the event to place it after. UNMOVE: where the cancelled move put it.
    after_number: int | None = None


class ApplyStageConsoleAction:
    """Apply what the stage console (FestEngine) did, as its service user.

    Events are addressed by number, the only key both sides share. The edits
    run through ``ScheduleOperations``, like an organizer's (docs/adr/0048).
    """

    def __init__(
        self,
        user_gateway: UserGateway,
        perm_service: PermissionService,
        schedule_gateway: ScheduleEntryGateway,
        changes_gateway: ScheduleChangeGateway,
        schedule_operations: ScheduleOperations,
    ) -> None:
        self.user_gateway = user_gateway
        self.perm_service = perm_service
        self.schedule_gateway = schedule_gateway
        self.changes_gateway = changes_gateway
        self.schedule_operations = schedule_operations

    async def __call__(self, data: ApplyStageConsoleActionInput) -> bool:
        """Return whether the schedule changed."""
        actor = await self.user_gateway.get_by_id(STAGE_CONSOLE_USER_ID)
        if actor is None:
            raise UserNotFound
        await self.perm_service.ensure(
            user=actor, permission=Permission.SCHEDULE_MANAGE
        )
        # Re-entrant: the operations take it again within this transaction.
        await self.schedule_gateway.lock_for_edit()
        event = await self._require_event(data.number)

        match data.action:
            case StageConsoleAction.SET_CURRENT:
                return await self.schedule_operations.set_current(actor, event.id)
            case StageConsoleAction.SKIP | StageConsoleAction.UNSKIP:
                return await self.schedule_operations.set_skipped(
                    actor,
                    event.id,
                    is_skipped=data.action is StageConsoleAction.SKIP,
                )
            case StageConsoleAction.MOVE:
                after_event = await self._require_event(data.after_number)
                return await self.schedule_operations.move(
                    actor, event.id, after_event.id
                )
            case StageConsoleAction.UNMOVE:
                return await self._unmove(actor, event, data.after_number)

    async def _require_event(self, number: int | None) -> ScheduleEvent:
        if number is None:
            raise EventNotFound
        event = await self.schedule_gateway.get_event_by_number(number)
        if event is None:
            raise EventNotFound
        return event

    async def _unmove(
        self, actor: User, event: ScheduleEvent, after_number: int | None
    ) -> bool:
        """Move the event back, but only while it still sits where the console put it.

        Any other state (an organizer moved it since, or a retry already moved
        it back) is left alone rather than guessed at.
        """
        latest_change = await self.changes_gateway.get_latest_for_event(event.id)
        moved_by_console = (
            latest_change is not None
            and latest_change.type is ScheduleChangeType.MOVED
            and latest_change.user_id == STAGE_CONSOLE_USER_ID
        )
        previous_entry = await self.schedule_gateway.get_previous_by_order(event.order)
        still_in_place = (
            after_number is not None
            and isinstance(previous_entry, ScheduleEvent)
            and previous_entry.number == after_number
        )
        if latest_change is None or not moved_by_console or not still_in_place:
            logger.warning(
                "Stage console unmove ignored",
                extra={
                    "event_id": str(event.id),
                    "moved_by_console": moved_by_console,
                    "still_in_place": still_in_place,
                },
            )
            return False
        return await self.schedule_operations.move(
            actor, event.id, latest_change.related_entry_id
        )
