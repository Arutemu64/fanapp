import pytest

from fanfan.application.interactors.festengine.notes import (
    NoteActions,
    diff_notes,
    move_target,
    parse_act_number,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        ("", "-", NoteActions(skip=True)),
        ("", "- сломался реквизит", NoteActions(skip=True)),
        ("-", "", NoteActions(skip=False)),
        ("- нет на месте", "пришли", NoteActions(skip=False)),
        ("", ">305", NoteActions(move_to=305)),
        (">305", ">310", NoteActions(move_to=310)),
        (">305", "", NoteActions(unmove=True)),
        ("", "->305", NoteActions(skip=True, move_to=305)),
        ("", ">305a", NoteActions(move_to=305)),
        ("", ">305 maybe", NoteActions(move_to=305)),
        ("", "поставить >152a позже", NoteActions(move_to=152)),
    ],
)
def test_marker_changes_produce_actions(
    previous: str, current: str, expected: NoteActions
) -> None:
    assert diff_notes(previous, current) == expected


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        ("", "2-3 min"),
        ("", ">5"),
        ("", ">30"),
        ("свет синий", "свет красный"),
        ("-", "- уже точно"),
        (">305", ">305 maybe"),
        (">305", ">305a"),
        ("", ""),
    ],
)
def test_unchanged_markers_produce_nothing(previous: str, current: str) -> None:
    assert diff_notes(previous, current).is_empty


@pytest.mark.parametrize(
    ("note", "expected"),
    [
        (">234", 234),
        (">305a", 305),
        (">152a maybe", 152),
        (">007", 7),
        (">5", None),
        ("305", None),
        (">305x7", 305),
    ],
)
def test_move_target_follows_festengine_regex(note: str, expected: int | None) -> None:
    assert move_target(note) == expected


@pytest.mark.parametrize(
    ("num", "expected"),
    [
        ("183", 183),
        ("007", 7),
        ("305a", 305),
        ("brk", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_act_number(num: str | None, expected: int | None) -> None:
    assert parse_act_number(num) == expected
