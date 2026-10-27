"""FestEngine's webhook payload and what fanapp makes of it.

The wire contract is FestEngine's; see docs/backend.md "FestEngine webhook".
Receivers ignore unknown types and fields, so every field here is optional.
"""

import re
from datetime import datetime, timedelta

from pydantic import AwareDatetime, BaseModel

from fanfan.application.interactors.schedule_mgmt.apply_stage_console_action import (
    ApplyStageConsoleActionInput,
    StageConsoleAction,
)

# A show cue that arrives later than this would move "now on stage" backwards.
CUE_MAX_AGE = timedelta(seconds=60)

_LEADING_DIGITS = re.compile(r"\d+")
_STAGE_ROW_TYPES = frozenset({"track", "dup"})
_CUE_TYPES = frozenset({"row.show", "row.play"})
_PLACING_ACTIONS = frozenset({StageConsoleAction.MOVE, StageConsoleAction.UNMOVE})
_ACTIONS = {
    "row.show": StageConsoleAction.SET_CURRENT,
    "row.play": StageConsoleAction.SET_CURRENT,
    "row.skip": StageConsoleAction.SKIP,
    "row.unskip": StageConsoleAction.UNSKIP,
    "row.move": StageConsoleAction.MOVE,
    "row.unmove": StageConsoleAction.UNMOVE,
}


class FestEngineRow(BaseModel):
    num: str | None = None
    row_type: str | None = None


class FestEngineEventData(BaseModel):
    row: FestEngineRow | None = None
    after_num: str | None = None


class FestEngineEvent(BaseModel):
    type: str
    timestamp: AwareDatetime
    data: FestEngineEventData = FestEngineEventData()

    def is_stale(self, now: datetime) -> bool:
        return self.type in _CUE_TYPES and now - self.timestamp > CUE_MAX_AGE


def parse_number(num: str | None) -> int | None:
    """The act number in a FestEngine №: its leading digits ("007" -> 7)."""
    if num is None:
        return None
    match = _LEADING_DIGITS.match(num)
    return int(match.group()) if match else None


def to_action_input(event: FestEngineEvent) -> ApplyStageConsoleActionInput | None:
    """The schedule edit an event asks for, or None when fanapp ignores it."""
    action = _ACTIONS.get(event.type)
    row = event.data.row
    if action is None or row is None:
        return None
    if (
        action is StageConsoleAction.SET_CURRENT
        and row.row_type not in _STAGE_ROW_TYPES
    ):
        return None
    number = parse_number(row.num)
    after_number = parse_number(event.data.after_num)
    if number is None:
        return None
    if action in _PLACING_ACTIONS and after_number is None:
        return None
    return ApplyStageConsoleActionInput(
        action=action, number=number, after_number=after_number
    )
