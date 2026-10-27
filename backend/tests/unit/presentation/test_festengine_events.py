from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from fanfan.application.interactors.schedule_mgmt.apply_stage_console_action import (
    ApplyStageConsoleActionInput,
    StageConsoleAction,
)
from fanfan.presentation.web.festengine.events import (
    FestEngineEvent,
    parse_number,
    to_action_input,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 27, 15, 0, tzinfo=UTC)


def _event(
    event_type: str, *, row: dict[str, Any] | None, **data: Any
) -> FestEngineEvent:
    return FestEngineEvent.model_validate(
        {
            "type": event_type,
            "timestamp": NOW.isoformat(),
            "data": {"row": row, **data},
        }
    )


def _row(num: str | None = "116", row_type: str = "track") -> dict[str, Any]:
    return {
        "num": num,
        "grid_num": num,
        "row_type": row_type,
        "fields": {"name": "Kaoru — Trinity Blood"},
        "notes": "",
    }


@pytest.mark.parametrize(
    ("num", "expected"),
    [("007", 7), ("116", 116), ("183a", 183), ("brk", None), ("", None), (None, None)],
)
def test_parse_number_reads_leading_digits(
    num: str | None, expected: int | None
) -> None:
    assert parse_number(num) == expected


@pytest.mark.parametrize("event_type", ["row.show", "row.play"])
@pytest.mark.parametrize("row_type", ["track", "dup"])
def test_show_and_play_set_the_act_current(event_type: str, row_type: str) -> None:
    event = _event(event_type, row=_row(row_type=row_type))

    assert to_action_input(event) == ApplyStageConsoleActionInput(
        action=StageConsoleAction.SET_CURRENT, number=116
    )


def test_countdown_show_is_ignored() -> None:
    event = _event("row.show", row=_row(num=None, row_type="countdown"))

    assert to_action_input(event) is None


@pytest.mark.parametrize(
    ("event_type", "action"),
    [
        ("row.skip", StageConsoleAction.SKIP),
        ("row.unskip", StageConsoleAction.UNSKIP),
    ],
)
def test_skip_facts_map_to_skip_actions(
    event_type: str, action: StageConsoleAction
) -> None:
    event = _event(event_type, row=_row())

    assert to_action_input(event) == ApplyStageConsoleActionInput(
        action=action, number=116
    )


@pytest.mark.parametrize(
    ("event_type", "action"),
    [
        ("row.move", StageConsoleAction.MOVE),
        ("row.unmove", StageConsoleAction.UNMOVE),
    ],
)
def test_move_facts_carry_the_after_number(
    event_type: str, action: StageConsoleAction
) -> None:
    event = _event(event_type, row=_row(), after_num="200", dup_grid_num="200a")

    assert to_action_input(event) == ApplyStageConsoleActionInput(
        action=action, number=116, after_number=200
    )


@pytest.mark.parametrize(
    "event_type",
    ["row.updated", "row.stop", "row.end", "hook.test", "something.new"],
)
def test_other_events_are_ignored(event_type: str) -> None:
    event = _event(event_type, row=_row(), previous={"notes": ""})

    assert to_action_input(event) is None


def test_event_without_a_row_is_ignored() -> None:
    assert to_action_input(_event("row.skip", row=None)) is None


def test_old_show_cue_is_stale() -> None:
    event = _event("row.show", row=_row())

    assert event.is_stale(NOW + timedelta(seconds=61))
    assert not event.is_stale(NOW + timedelta(seconds=59))


def test_old_state_change_is_not_stale() -> None:
    event = _event("row.skip", row=_row())

    assert not event.is_stale(NOW + timedelta(minutes=9))
