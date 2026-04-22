from typing import Any

from pydantic import BaseModel, Field


class ErrorMessage(BaseModel):
    code: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationErrorDetail(BaseModel):
    loc: list[str | int]
    type: str


class ValidationErrorResponse(BaseModel):
    code: str = "VALIDATION_ERROR"
    details: dict[str, list[ValidationErrorDetail]] = Field(default_factory=dict)
