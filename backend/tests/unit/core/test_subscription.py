import pytest

from fanfan.core.models.subscription import REMINDER_POSITIONS_AHEAD, is_reminder_due


@pytest.mark.parametrize(
    ("positions_ahead", "seconds_ahead", "expected"),
    [
        # Within the lead time by the estimate.
        (5, 15 * 60, True),
        # Outside it, and far from the stage.
        (5, 15 * 60 + 1, False),
        # Outside it by the estimate, but close enough by the running order:
        # durations of zero or too short must not delay the reminder past here.
        (REMINDER_POSITIONS_AHEAD, 60 * 60, True),
        (REMINDER_POSITIONS_AHEAD + 1, 60 * 60, False),
        # On stage or passed: the "started" notice covers it, not a reminder.
        (0, 0, False),
        (-1, 0, False),
    ],
)
def test_is_reminder_due(
    positions_ahead: int, seconds_ahead: int, *, expected: bool
) -> None:
    assert (
        is_reminder_due(
            lead_minutes=15,
            positions_ahead=positions_ahead,
            seconds_ahead=seconds_ahead,
        )
        is expected
    )
