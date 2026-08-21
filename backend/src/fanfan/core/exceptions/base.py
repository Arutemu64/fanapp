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


# --- Semantic markers --------------------------------------------------------
# These carry no HTTP knowledge, so core stays framework-agnostic. The
# presentation layer maps each marker to an HTTP status (EXCEPTION_STATUS_MAP in
# web/exceptions.py), and status resolution walks the MRO, so a concrete
# exception gets its status from the marker it inherits. To add an exception,
# inherit the marker that fits its meaning instead of editing the status map.
#
# Convention: list the marker FIRST in the bases so it wins MRO precedence over
# the feature-grouping base, e.g. `class UserNotFound(NotFound, UserException)`.
# A completeness test (tests for the status map) fails if a concrete exception
# ends up with no marker and is not explicitly flagged as internal-only.


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
    # Doubles as the "forbidden" marker (403) and a concrete exception raised
    # directly with a `reason` detail.
    code = "ACCESS_DENIED"
