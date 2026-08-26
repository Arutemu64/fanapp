from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fanfan.application.interactors.settings.update_settings import (
    UpdateAppSettingsInput,
)

pytestmark = pytest.mark.unit


def test_festival_boundaries_require_an_offset():
    # A naive festival boundary is rejected at the schema, before the range check
    # can compare it against the tz-aware persisted counterpart — that comparison
    # would otherwise raise TypeError (a 500) instead of this clean 422.
    with pytest.raises(ValidationError):
        # The missing tzinfo is the point of the test — that is what must be rejected.
        UpdateAppSettingsInput(festival_end=datetime(2026, 8, 23, 20, 0))  # noqa: DTZ001


def test_festival_boundaries_accept_an_aware_instant():
    aware = datetime(2026, 8, 23, 20, 0, tzinfo=UTC)

    parsed = UpdateAppSettingsInput(festival_end=aware)

    assert parsed.festival_end == aware
