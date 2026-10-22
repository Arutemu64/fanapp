import pytest

from fanfan.core.exceptions.schedule import (
    InvalidScheduleFile,
    InvalidScheduleFileReason,
)
from fanfan.presentation.web.schemas.error import InvalidScheduleFileError

pytestmark = pytest.mark.unit


# InvalidScheduleFileError only documents the response; the body is built from
# the exception's details dict. This keeps the documented shape honest.
@pytest.mark.parametrize("reason", list(InvalidScheduleFileReason))
def test_invalid_schedule_file_details_match_the_documented_model(
    reason: InvalidScheduleFileReason,
) -> None:
    exc = InvalidScheduleFile(reason, columns=["A"], column="B", row=3, number=7)

    documented = InvalidScheduleFileError.model_validate(
        {"code": exc.code, "details": exc.details}
    )

    assert documented.details.model_dump(mode="json") == exc.details
