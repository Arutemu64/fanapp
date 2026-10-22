from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fanfan.core.exceptions.schedule import InvalidScheduleFileReason

# The code the validation handler emits; referenced from the OpenAPI code-enum
# builder so it appears in the client-facing union alongside domain codes.
VALIDATION_ERROR_CODE = "VALIDATION_ERROR"


# RFC 9457 §3: problem details serialized as JSON carry this media type.
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
    # The status phrase: the client never shows server text (it picks Russian
    # copy from `code`), so a per-code English title would go unread.
    title: str
    status: int
    code: str


# A Pydantic error's `ctx` keeps only these: it carries the limit the input broke
# (`max_length`, `ge`, …) for copy like "at most 500 characters", but a custom
# validator can put an exception object there too.
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
    # What locates the problem; which of these are set depends on the reason.
    columns: list[str] | None = None
    column: str | None = None
    row: int | None = None
    number: int | None = None
