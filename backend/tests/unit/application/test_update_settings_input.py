from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fanfan.application.interactors.schedule_mgmt.schedule_settings import (
    UpdateScheduleSettingsInput,
)
from fanfan.application.interactors.settings.update_settings import (
    UpdateAppSettingsInput,
)

pytestmark = pytest.mark.unit


def test_festival_boundaries_require_an_offset() -> None:
    # A naive festival boundary is rejected at the schema, before the range check
    # can compare it against the tz-aware persisted counterpart — that comparison
    # would otherwise raise TypeError (a 500) instead of this clean 422.
    with pytest.raises(ValidationError) as exc_info:
        # The missing tzinfo is the point of the test — that is what must be rejected.
        UpdateAppSettingsInput(festival_end=datetime(2026, 8, 23, 20, 0))  # noqa: DTZ001

    assert [error["loc"] for error in exc_info.value.errors()] == [("festival_end",)]


def test_festival_boundaries_accept_an_aware_instant() -> None:
    aware = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)

    parsed = UpdateAppSettingsInput(festival_end=aware)

    assert parsed.festival_end == aware


@pytest.mark.parametrize(
    ("payload", "loc"),
    [
        ({"festival_end": None}, ("festival_end",)),
        ({"quest": None}, ("quest",)),
        ({"quest": {"max_award": None}}, ("quest", "max_award")),
    ],
)
def test_explicit_null_is_rejected_rather_than_ignored(
    payload: dict[str, object], loc: tuple[str, ...]
) -> None:
    # None of these can be cleared, so a null must not read as "leave as is".
    with pytest.raises(ValidationError) as exc_info:
        UpdateAppSettingsInput.model_validate(payload)

    assert [error["loc"] for error in exc_info.value.errors()] == [loc]


def test_omitted_fields_stay_unset() -> None:
    parsed = UpdateAppSettingsInput.model_validate({"quest": {"enabled": True}})

    assert parsed.festival_start is None
    assert parsed.quest.model_fields_set == {"enabled"}


def test_schedule_settings_reject_an_explicit_null() -> None:
    with pytest.raises(ValidationError):
        UpdateScheduleSettingsInput.model_validate({"changeover_seconds": None})
