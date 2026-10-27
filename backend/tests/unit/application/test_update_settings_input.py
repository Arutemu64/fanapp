from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fanfan.application.interactors.settings.update_settings import (
    UpdateAppSettingsInput,
)

pytestmark = pytest.mark.unit


def test_festival_boundaries_require_an_offset() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UpdateAppSettingsInput(festival_end=datetime(2026, 8, 23, 20, 0))  # noqa: DTZ001

    assert [error["loc"] for error in exc_info.value.errors()] == [("festival_end",)]


def test_festival_boundaries_accept_an_aware_instant() -> None:
    aware = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)

    parsed = UpdateAppSettingsInput(festival_end=aware)

    assert parsed.festival_end == aware
