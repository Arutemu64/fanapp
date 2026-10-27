"""How FestEngine notes map to schedule actions (docs/adr/0048-festengine-webhooks.md).

Actions fire on a change between the old and the new note, never on the note
as it stands. Re-saving a note for another reason then leaves alone what an
organizer has decided in fanapp since.
"""

import re
from dataclasses import dataclass

SKIP_MARKER = "-"
# FestEngine's own pattern (main.pyw, on_grid_cell_changed). A different one
# would move acts that FestEngine leaves in place.
MOVE_PATTERN = re.compile(r">(\d{3}(\w)?)([^\w].*)?")
MOVE_TARGET_DIGITS = 3
LEADING_DIGITS = re.compile(r"[0-9]+")


@dataclass(frozen=True, slots=True, kw_only=True)
class NoteActions:
    """True skips, False unskips, None leaves the skip state alone."""

    skip: bool | None = None
    move_to: int | None = None
    unmove: bool = False

    @property
    def is_empty(self) -> bool:
        return self.skip is None and self.move_to is None and not self.unmove


def is_skip_note(note: str) -> bool:
    """Only the first character counts: "2-3 min" is ordinary text."""
    return note.startswith(SKIP_MARKER)


def move_target(note: str) -> int | None:
    """The act number after ">", without FestEngine's letter suffix (>305a → 305)."""
    match = MOVE_PATTERN.search(note)
    if match is None:
        return None
    return int(match.group(1)[:MOVE_TARGET_DIGITS])


def diff_notes(previous: str, current: str) -> NoteActions:
    skip: bool | None = None
    if is_skip_note(current) != is_skip_note(previous):
        skip = is_skip_note(current)

    target_before = move_target(previous)
    target_now = move_target(current)
    move_to = target_now if target_now != target_before else None
    unmove = target_before is not None and target_now is None

    return NoteActions(skip=skip, move_to=move_to, unmove=unmove)


def parse_act_number(num: str | None) -> int | None:
    """The leading digits of FestEngine's ``num`` ("007" → 7), or None."""
    if num is None:
        return None
    match = LEADING_DIGITS.match(num)
    if match is None:
        return None
    return int(match.group())
