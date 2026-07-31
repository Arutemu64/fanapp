import pytest

from fanfan.application.dto.schedule_change import (
    ScheduleChangeEventDTO,
    ScheduleChangeFullDTO,
)
from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
)
from fanfan.core.vo.schedule_change import (
    ScheduleChangeType,
    generate_schedule_change_id,
)
from fanfan.core.vo.schedule_event import generate_schedule_event_id

pytestmark = pytest.mark.unit


def _event(number: int | None, title: str) -> ScheduleChangeEventDTO:
    return ScheduleChangeEventDTO(
        id=generate_schedule_event_id(),
        number=number,
        title=title,
        order=1.0,
    )


def _change(
    change_type: ScheduleChangeType,
    *,
    changed_event: ScheduleChangeEventDTO | None = None,
    argument_event: ScheduleChangeEventDTO | None = None,
) -> ScheduleChangeFullDTO:
    return ScheduleChangeFullDTO(
        id=generate_schedule_change_id(),
        type=change_type,
        mailing_id=None,
        user_id=None,
        next_event_changed=False,
        changed_event=changed_event,
        argument_event=argument_event,
        user=None,
    )


@pytest.mark.parametrize(
    ("change_type", "expected"),
    [
        (ScheduleChangeType.SET_AS_CURRENT, "Выступление №007 началось"),
        (ScheduleChangeType.MOVED, "Выступление №007 перенесено"),
        (ScheduleChangeType.SKIPPED, "Выступление №007 было снято"),
        (ScheduleChangeType.UNSKIPPED, "Выступление №007 вернулось"),
    ],
)
def test_numbered_event_is_named_by_its_padded_number(
    change_type: ScheduleChangeType, expected: str
) -> None:
    change = _change(change_type, changed_event=_event(7, "Дефиле"))

    assert SendScheduleChangeNotifications._resolve_reason_msg(change) == expected


@pytest.mark.parametrize(
    ("change_type", "expected"),
    [
        (ScheduleChangeType.SET_AS_CURRENT, "Выступление «Перерыв» началось"),
        (ScheduleChangeType.MOVED, "Выступление «Перерыв» перенесено"),
        (ScheduleChangeType.SKIPPED, "Выступление «Перерыв» было снято"),
        (ScheduleChangeType.UNSKIPPED, "Выступление «Перерыв» вернулось"),
    ],
)
def test_numberless_event_is_named_by_its_title(
    change_type: ScheduleChangeType, expected: str
) -> None:
    # A break has no number to print; formatting one anyway used to crash the
    # whole notification fan-out on `f"{None:03d}"`.
    change = _change(change_type, changed_event=_event(None, "Перерыв"))

    assert SendScheduleChangeNotifications._resolve_reason_msg(change) == expected


def test_unset_current_names_the_event_that_was_on_stage() -> None:
    change = _change(
        ScheduleChangeType.SET_AS_CURRENT,
        argument_event=_event(None, "Перерыв"),
    )

    assert (
        SendScheduleChangeNotifications._resolve_reason_msg(change)
        == "Выступление «Перерыв» больше не текущее"
    )
