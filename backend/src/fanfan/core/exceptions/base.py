from collections.abc import Mapping
from typing import Any, ClassVar


class AppException(Exception):
    code: ClassVar[str] = "UNKNOWN"

    def __init__(
        self,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.details = dict(details or {})
        super().__init__(self.code)

    def __str__(self) -> str:
        return self.code


class AccessDenied(AppException):
    code = "ACCESS_DENIED"
