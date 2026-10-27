from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fanfan.core.exceptions.schedule import InvalidScheduleFileReason

VALIDATION_ERROR_CODE = "VALIDATION_ERROR"


PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"


class ProblemDetails(BaseModel):
    """An RFC 9457 problem details object; every error response is one.

    `code` is our extension member and what the client branches on: a closed
    set, stamped into the spec as an enum. `type` is derived from it, so the two
    never disagree. Problem-specific members (`retry_after`, `reason`, `errors`,
    …) sit beside these at the top level, as RFC 9457 §3.2 extensions do.
    """

    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    code: str


ValidationContextValue = str | int | float | bool


class ValidationErrorDetail(BaseModel):
    loc: list[str | int]
    type: str
    ctx: dict[str, ValidationContextValue] = Field(default_factory=dict)


class ValidationProblem(ProblemDetails):
    code: Literal["VALIDATION_ERROR"]
    errors: list[ValidationErrorDetail]


class InvalidScheduleFileProblem(ProblemDetails):
    """ProblemDetails narrowed to INVALID_SCHEDULE_FILE, for the import route's docs.

    Gives the frontend a typed `reason` union to check its copy against, as the
    code enum does for codes. The response itself is still built from the
    exception's details dict; a unit test keeps the two in step.
    """

    code: Literal["INVALID_SCHEDULE_FILE"]
    reason: InvalidScheduleFileReason
    columns: list[str] | None = None
    column: str | None = None
    row: int | None = None
    number: int | None = None
