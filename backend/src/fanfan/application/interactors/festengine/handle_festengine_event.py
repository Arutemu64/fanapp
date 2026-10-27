import enum
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pydantic import AwareDatetime, BaseModel

from fanfan.application.interactors.festengine.notes import (
    NoteActions,
    diff_notes,
    parse_act_number,
)
from fanfan.application.interactors.schedule_mgmt.move_schedule_event import (
    MoveScheduleEvent,
    MoveScheduleEventInput,
)
from fanfan.application.interactors.schedule_mgmt.set_current_schedule_event import (
    SetCurrentScheduleEvent,
    SetCurrentScheduleEventInput,
)
from fanfan.application.interactors.schedule_mgmt.update_schedule_event_skip import (
    UpdateScheduleEventSkip,
    UpdateScheduleEventSkipInput,
)
from fanfan.application.ports.gateways.schedule_changes import (
    ScheduleChangeGateway,
)
from fanfan.application.ports.gateways.schedule_entries import (
    ScheduleEntryGateway,
)
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.exceptions.users import UserNotFound
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_change import ScheduleChangeType
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.core.vo.user import SYSTEM_USER_ID

logger = logging.getLogger(__name__)

CUE_TYPES = frozenset({"row.show", "row.play"})
ROW_UPDATED = "row.updated"
ACT_ROW_TYPES = frozenset({"track", "dup"})
EDITABLE_ROW_TYPE = "track"
# Below FestEngine's own 120 s cutoff: a cue held back by an outage must not
# move "now on stage" backwards.
CUE_MAX_AGE = timedelta(seconds=60)


class FestEnginePrevious(BaseModel):
    notes: str | None = None


class FestEngineRowData(BaseModel):
    """The row fields fanapp reads; every other field FestEngine sends is ignored."""

    num: str | None = None
    row_type: str | None = None
    notes: str | None = None
    previous: FestEnginePrevious | None = None


class FestEngineEventInput(BaseModel):
    type: str
    timestamp: AwareDatetime
    data: FestEngineRowData = FestEngineRowData()


class FestEngineEventStatus(enum.StrEnum):
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    IGNORED = "ignored"
    STALE = "stale"


class FestEngineAction(enum.StrEnum):
    SET_CURRENT = "set_current"
    SKIP = "skip"
    UNSKIP = "unskip"
    MOVE = "move"
    UNMOVE = "unmove"


class FestEngineEventOutput(BaseModel):
    status: FestEngineEventStatus
    actions: list[FestEngineAction]


IGNORED = FestEngineEventOutput(status=FestEngineEventStatus.IGNORED, actions=[])
UNCHANGED = FestEngineEventOutput(status=FestEngineEventStatus.UNCHANGED, actions=[])


@dataclass(frozen=True, slots=True, kw_only=True)
class _UnmoveTarget:
    """Where an unmove puts the act back; None after means first."""

    place_after_entry_id: ScheduleEntryId | None


class HandleFestEngineEvent:
    """Turns one FestEngine webhook event into schedule edits.

    Acts as the system user, as cron and the CLI do: the request has no session
    (docs/adr/0048-festengine-webhooks.md). Each action is an ordinary announced
    edit, so a second action in the same event can hit the announcement
    cooldown; FestEngine retries on 429 and the first action is then a no-op.
    """

    def __init__(
        self,
        schedule_gateway: ScheduleEntryGateway,
        changes_gateway: ScheduleChangeGateway,
        user_gateway: UserGateway,
        perm_service: PermissionService,
        set_current: SetCurrentScheduleEvent,
        update_skip: UpdateScheduleEventSkip,
        move: MoveScheduleEvent,
    ) -> None:
        self.schedule_gateway = schedule_gateway
        self.changes_gateway = changes_gateway
        self.user_gateway = user_gateway
        self.perm_service = perm_service
        self.set_current = set_current
        self.update_skip = update_skip
        self.move = move

    async def __call__(self, data: FestEngineEventInput) -> FestEngineEventOutput:
        if data.type in CUE_TYPES:
            return await self._handle_cue(data)
        if data.type == ROW_UPDATED:
            return await self._handle_row_updated(data)
        return IGNORED

    async def _handle_cue(self, data: FestEngineEventInput) -> FestEngineEventOutput:
        number = parse_act_number(data.data.num)
        if data.data.row_type not in ACT_ROW_TYPES or number is None:
            return IGNORED
        if datetime.now(UTC) - data.timestamp > CUE_MAX_AGE:
            return FestEngineEventOutput(status=FestEngineEventStatus.STALE, actions=[])

        actor = await self._system_actor()
        await self.schedule_gateway.lock_for_edit()
        event = await self._require_event(number)
        changed = await self.set_current(
            SetCurrentScheduleEventInput(event_id=event.id), actor=actor
        )
        if not changed:
            return UNCHANGED
        return FestEngineEventOutput(
            status=FestEngineEventStatus.UPDATED,
            actions=[FestEngineAction.SET_CURRENT],
        )

    async def _handle_row_updated(
        self, data: FestEngineEventInput
    ) -> FestEngineEventOutput:
        row = data.data
        number = parse_act_number(row.num)
        if row.row_type != EDITABLE_ROW_TYPE or number is None:
            return IGNORED
        if row.previous is None or row.previous.notes is None:
            return IGNORED

        note_actions = diff_notes(row.previous.notes, row.notes or "")
        if note_actions.is_empty:
            return UNCHANGED

        actor = await self._system_actor()
        # Resolve everything under one lock; each action below commits on its own.
        await self.schedule_gateway.lock_for_edit()
        event = await self._require_event(number)
        move_target = await self._resolve_move_target(note_actions)
        unmove_target = await self._resolve_unmove_target(note_actions, event)

        applied = await self._apply_skip(note_actions, event, actor)
        applied += await self._apply_move(event, move_target, unmove_target, actor)
        if not applied:
            return UNCHANGED
        return FestEngineEventOutput(
            status=FestEngineEventStatus.UPDATED, actions=applied
        )

    async def _system_actor(self) -> User:
        user = await self.user_gateway.get_by_id(SYSTEM_USER_ID)
        if user is None:
            raise UserNotFound
        await self.perm_service.ensure(user=user, permission=Permission.SCHEDULE_MANAGE)
        return user

    async def _require_event(self, number: int) -> ScheduleEvent:
        event = await self.schedule_gateway.get_event_by_number(number)
        if event is None:
            raise EventNotFound
        return event

    async def _resolve_move_target(
        self, note_actions: NoteActions
    ) -> ScheduleEvent | None:
        """Mirrors FestEngine's bisect: NNN, else the closest lower number."""
        if note_actions.move_to is None:
            return None
        target = await self.schedule_gateway.get_last_event_numbered_at_most(
            note_actions.move_to
        )
        if target is None:
            raise EventNotFound
        return target

    async def _resolve_unmove_target(
        self, note_actions: NoteActions, event: ScheduleEvent
    ) -> _UnmoveTarget | None:
        """Only a move FestEngine made is undone; an organizer's later one stays.

        The webhook is the only code that records MOVED as the system user, so
        such a change means "the last move came from FestEngine".
        """
        if not note_actions.unmove:
            return None
        change = await self.changes_gateway.get_latest_for_event(event.id)
        if (
            change is None
            or change.type is not ScheduleChangeType.MOVED
            or change.user_id != SYSTEM_USER_ID
        ):
            logger.warning(
                "FestEngine unmove skipped: last change is not a FestEngine move",
                extra={"event_id": str(event.id)},
            )
            return None
        return _UnmoveTarget(place_after_entry_id=change.related_entry_id)

    async def _apply_skip(
        self, note_actions: NoteActions, event: ScheduleEvent, actor: User
    ) -> list[FestEngineAction]:
        if note_actions.skip is None:
            return []
        changed = await self.update_skip(
            UpdateScheduleEventSkipInput(
                event_id=event.id, is_skipped=note_actions.skip
            ),
            actor=actor,
        )
        if not changed:
            return []
        if note_actions.skip:
            return [FestEngineAction.SKIP]
        return [FestEngineAction.UNSKIP]

    async def _apply_move(
        self,
        event: ScheduleEvent,
        move_target: ScheduleEvent | None,
        unmove_target: _UnmoveTarget | None,
        actor: User,
    ) -> list[FestEngineAction]:
        if move_target is not None:
            if await self._move(event, move_target.id, actor):
                return [FestEngineAction.MOVE]
            return []
        if unmove_target is not None:
            target_id = unmove_target.place_after_entry_id
            if await self._move(event, target_id, actor):
                return [FestEngineAction.UNMOVE]
        return []

    async def _move(
        self,
        event: ScheduleEvent,
        place_after_entry_id: ScheduleEntryId | None,
        actor: User,
    ) -> bool:
        return await self.move(
            MoveScheduleEventInput(
                event_id=event.id, place_after_entry_id=place_after_entry_id
            ),
            actor=actor,
        )
