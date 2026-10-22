import pytest
from pydantic import MISSING, ValidationError

from fanfan.application.interactors.current_user.update_current_user import (
    UpdateCurrentUserInput,
)
from fanfan.application.interactors.current_user.update_user_settings import (
    UpdateUserSettingsInput,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("field", ["username", "avatar_seed"])
def test_profile_rejects_an_explicit_null(field: str) -> None:
    # Neither can be cleared, so a null must not read as "leave as is".
    with pytest.raises(ValidationError) as exc_info:
        UpdateCurrentUserInput.model_validate({field: None})

    assert [error["loc"] for error in exc_info.value.errors()] == [(field,)]


def test_profile_omitted_fields_stay_missing() -> None:
    parsed = UpdateCurrentUserInput.model_validate({"avatar_seed": "fresh-seed_1"})

    assert parsed.username is MISSING
    assert parsed.model_dump() == {"avatar_seed": "fresh-seed_1"}


def test_settings_reject_an_explicit_null() -> None:
    with pytest.raises(ValidationError) as exc_info:
        UpdateUserSettingsInput.model_validate({"receive_vk_notifications": None})

    assert [error["loc"] for error in exc_info.value.errors()] == [
        ("receive_vk_notifications",)
    ]


def test_settings_dump_only_what_was_sent() -> None:
    parsed = UpdateUserSettingsInput.model_validate(
        {"receive_all_announcements": False}
    )

    assert parsed.model_dump() == {"receive_all_announcements": False}
