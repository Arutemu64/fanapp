from typing import Any, Literal

from pydantic import BaseModel, Field

from fanfan.core.exceptions.schedule import InvalidScheduleFileReason

# The code the validation handler emits; referenced from the OpenAPI code-enum
# builder so it appears in the client-facing union alongside domain codes.
VALIDATION_ERROR_CODE = "VALIDATION_ERROR"


class ErrorMessage(BaseModel):
    code: str
    details: dict[str, Any] = Field(default_factory=dict)


# A Pydantic error's `ctx` keeps only these: it carries the limit the input broke
# (`max_length`, `ge`, …) for copy like "at most 500 characters", but a custom
# validator can put an exception object there too.
ValidationContextValue = str | int | float | bool


class ValidationErrorDetail(BaseModel):
    loc: list[str | int]
    type: str
    ctx: dict[str, ValidationContextValue] = Field(default_factory=dict)


class ValidationErrorResponse(BaseModel):
    code: str = VALIDATION_ERROR_CODE
    details: dict[str, list[ValidationErrorDetail]] = Field(default_factory=dict)


class InvalidScheduleFileDetails(BaseModel):
    reason: InvalidScheduleFileReason
    # What locates the problem; which of these are set depends on the reason.
    columns: list[str] | None = None
    column: str | None = None
    row: int | None = None
    number: int | None = None


class InvalidScheduleFileError(BaseModel):
    """ErrorMessage narrowed to INVALID_SCHEDULE_FILE, for the import route's docs.

    Gives the frontend a typed `reason` union to check its copy against, as the
    code enum does for codes. The response itself is still built from the
    exception's details dict; a unit test keeps the two in step.
    """

    code: Literal["INVALID_SCHEDULE_FILE"]
    details: InvalidScheduleFileDetails
