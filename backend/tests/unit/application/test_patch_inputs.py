"""PATCH bodies follow JSON Merge Patch (RFC 7396).

A missing field leaves the value alone, and `null` would clear it, so a field
that cannot be cleared refuses `null` instead of reading it as "no change".
"""

from uuid import uuid7

import pytest
from pydantic import BaseModel, ValidationError

from fanfan.application.interactors.current_user.update_current_user import (
    UpdateCurrentUserInput,
)
from fanfan.application.interactors.current_user.update_user_settings import (
    UpdateUserSettingsInput,
)
from fanfan.application.interactors.schedule_mgmt.schedule_settings import (
    UpdateScheduleSettingsInput,
)
from fanfan.application.interactors.settings.update_settings import (
    UpdateAppSettingsInput,
)
from fanfan.presentation.web.schemas.schedule import UpdateScheduleEventBody

pytestmark = pytest.mark.unit

PATCH_FIELDS: list[tuple[type[BaseModel], str]] = [
    (UpdateCurrentUserInput, "username"),
    (UpdateCurrentUserInput, "avatar_seed"),
    (UpdateUserSettingsInput, "receive_all_announcements"),
    (UpdateUserSettingsInput, "receive_telegram_notifications"),
    (UpdateUserSettingsInput, "receive_vk_notifications"),
    (UpdateAppSettingsInput, "festival_start"),
    (UpdateAppSettingsInput, "festival_end"),
    (UpdateAppSettingsInput, "quest_enabled"),
    (UpdateAppSettingsInput, "quest_max_award"),
    (UpdateAppSettingsInput, "quest_cancel_window_minutes"),
    (UpdateScheduleSettingsInput, "announcement_timeout"),
    (UpdateScheduleSettingsInput, "changeover_seconds"),
    (UpdateScheduleEventBody, "is_skipped"),
]


@pytest.mark.parametrize(("model", "field"), PATCH_FIELDS)
def test_patch_field_refuses_null(model: type[BaseModel], field: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate({field: None})

    assert exc_info.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize(
    "model",
    [
        UpdateCurrentUserInput,
        UpdateUserSettingsInput,
        UpdateAppSettingsInput,
        UpdateScheduleSettingsInput,
    ],
)
def test_missing_patch_fields_stay_out_of_the_dump(model: type[BaseModel]) -> None:
    assert model.model_validate({}).model_dump() == {}


def test_patch_field_is_optional_and_not_nullable_in_the_schema() -> None:
    schema = UpdateAppSettingsInput.model_json_schema()

    assert "required" not in schema
    assert schema["properties"]["quest_enabled"] == {
        "title": "Quest Enabled",
        "type": "boolean",
    }


def test_null_predecessor_moves_the_event_to_the_top() -> None:
    body = UpdateScheduleEventBody.model_validate({"place_after_entry_id": None})

    assert body.model_fields_set == {"place_after_entry_id"}
    assert body.place_after_entry_id is None


def test_schedule_event_body_takes_exactly_one_change() -> None:
    with pytest.raises(ValidationError):
        UpdateScheduleEventBody.model_validate({})
    with pytest.raises(ValidationError):
        UpdateScheduleEventBody.model_validate(
            {"is_skipped": True, "place_after_entry_id": str(uuid7())}
        )
