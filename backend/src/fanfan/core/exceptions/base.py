from collections.abc import Mapping
from typing import Any, ClassVar, override


class AppException(Exception):
    code: ClassVar[str] = "UNKNOWN"

    def __init__(
        self,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.details = dict(details or {})
        super().__init__(self.code)

    @override
    def __str__(self) -> str:
        return self.code


class ConstraintViolation(AppException):
    """Invalid input, or an operation not allowed in the current state (400)."""


class NotFound(AppException):
    """A requested resource does not exist (404)."""


class Conflict(AppException):
    """The request conflicts with current state: duplicate, stale, etc. (409)."""


class RateLimited(AppException):
    """The caller exceeded an allowed rate; carries a retry_after detail (429)."""


class UpstreamServiceError(AppException):
    """A third-party service the app calls out to failed or was unreachable (502).

    The request itself is valid, so it is not a 500 (our bug) — the app acted as a
    gateway to an external provider (SMTP relay, vendor API) and that provider gave
    back a failed response. Distinguishing it lets the client show a "try again"
    message and keeps these transient outages out of the unhandled-error bucket.
    """


class AccessDenied(AppException):
    code = "ACCESS_DENIED"
