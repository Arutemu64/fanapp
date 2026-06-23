from typing import Any

from pydantic import BaseModel, Field

# The code the validation handler emits; referenced from the OpenAPI code-enum
# builder so it appears in the client-facing union alongside domain codes.
VALIDATION_ERROR_CODE = "VALIDATION_ERROR"


class ErrorMessage(BaseModel):
    code: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationErrorDetail(BaseModel):
    loc: list[str | int]
    type: str


class ValidationErrorResponse(BaseModel):
    code: str = VALIDATION_ERROR_CODE
    details: dict[str, list[ValidationErrorDetail]] = Field(default_factory=dict)
