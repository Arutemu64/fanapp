import pytest

from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    _rounded_wait_minutes,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (30, 1),
        (60, 1),
        (61, 2),
        (9 * 60, 9),
        (9 * 60 + 1, 10),
        (11 * 60, 15),
        (15 * 60, 15),
        (61 * 60, 65),
    ],
)
def test_wait_rounds_up_to_minutes_then_to_five_past_ten(
    seconds: int, expected: int
) -> None:
    assert _rounded_wait_minutes(seconds) == expected
