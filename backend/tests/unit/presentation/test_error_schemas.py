import json
from http import HTTPStatus

import pytest

from fanfan.core.exceptions.schedule import (
    InvalidScheduleFile,
    InvalidScheduleFileReason,
)
from fanfan.presentation.web.exceptions import problem_response
from fanfan.presentation.web.schemas.error import InvalidScheduleFileProblem

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("reason", list(InvalidScheduleFileReason))
def test_invalid_schedule_file_details_match_the_documented_model(
    reason: InvalidScheduleFileReason,
) -> None:
    exc = InvalidScheduleFile(reason, columns=["A"], column="B", row=3, number=7)

    response = problem_response(HTTPStatus.BAD_REQUEST, exc.code, exc.details)

    body = json.loads(bytes(response.body))

    InvalidScheduleFileProblem.model_validate(body)
    assert set(body) <= set(InvalidScheduleFileProblem.model_fields)
