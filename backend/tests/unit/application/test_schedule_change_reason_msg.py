from datetime import UTC, datetime
from typing import Any, cast

import pytest

from fanfan.adapters.jinja.factory import create_jinja_env
from fanfan.adapters.jinja.renderer import JinjaTemplateRenderer
from fanfan.application.dto.schedule_change import (
    ScheduleChangeEntryDTO,
    ScheduleChangeFullDTO,
)
from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
)
from fanfan.core.vo.schedule_change import (
    ScheduleChangeType,
    generate_schedule_change_id,
)
from fanfan.core.vo.schedule_entry import ScheduleEntryType, generate_schedule_entry_id

pytestmark = pytest.mark.unit


async def _reason_msg(change: ScheduleChangeFullDTO) -> str | None:
    # Only the renderer is touched; the gateways are never read.
    unused = cast("Any", object())
    interactor = SendScheduleChangeNotifications(
        JinjaTemplateRenderer(create_jinja_env()),
        unused,
        unused,
        unused,
        unused,
        unused,
        unused,
        unused,
        unused,
    )
    return await interactor._render_reason_msg(change)


def _event(number: int | None, title: str) -> ScheduleChangeEntryDTO:
    return ScheduleChangeEntryDTO(
        id=generate_schedule_entry_id(),
        type=ScheduleEntryType.EVENT,
        number=number,
        title=title,
        order=1.0,
    )


def _change(
    change_type: ScheduleChangeType,
    *,
    changed_event: ScheduleChangeEntryDTO | None = None,
    related_entry: ScheduleChangeEntryDTO | None = None,
) -> ScheduleChangeFullDTO:
    return ScheduleChangeFullDTO(
        id=generate_schedule_change_id(),
        type=change_type,
        mailing_id=None,
        next_event_changed=False,
        changed_event=changed_event,
        related_entry=related_entry,
        user=None,
        created_at=datetime.now(UTC),
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
async def test_numbered_event_is_named_by_its_padded_number(
    change_type: ScheduleChangeType, expected: str
) -> None:
    change = _change(change_type, changed_event=_event(7, "Дефиле"))

    assert await _reason_msg(change) == expected


@pytest.mark.parametrize(
    ("change_type", "expected"),
    [
        (ScheduleChangeType.SET_AS_CURRENT, "Выступление «Перерыв» началось"),
        (ScheduleChangeType.MOVED, "Выступление «Перерыв» перенесено"),
        (ScheduleChangeType.SKIPPED, "Выступление «Перерыв» было снято"),
        (ScheduleChangeType.UNSKIPPED, "Выступление «Перерыв» вернулось"),
    ],
)
async def test_numberless_event_is_named_by_its_title(
    change_type: ScheduleChangeType, expected: str
) -> None:
    # A break has no number to print; formatting one anyway would crash the
    # whole notification fan-out on `f"{None:03d}"`.
    change = _change(change_type, changed_event=_event(None, "Перерыв"))

    assert await _reason_msg(change) == expected


async def test_unset_current_names_the_event_that_was_on_stage() -> None:
    change = _change(
        ScheduleChangeType.SET_AS_CURRENT,
        related_entry=_event(None, "Перерыв"),
    )

    assert await _reason_msg(change) == "Выступление «Перерыв» больше не текущее"


async def test_change_without_an_event_has_no_reason() -> None:
    change = _change(ScheduleChangeType.MOVED)

    assert await _reason_msg(change) is None
