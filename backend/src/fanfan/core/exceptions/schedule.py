import enum
from typing import Any

from fanfan.core.exceptions.base import (
    AppException,
    Conflict,
    ConstraintViolation,
    NotFound,
    RateLimited,
)


class ScheduleException(AppException):
    pass


class InvalidScheduleFileReason(enum.StrEnum):
    """Why a schedule spreadsheet was rejected.

    Travels to the client inside the error `details`, so each member is part of
    the API contract — the frontend switches on it to pick Russian copy.
    """

    UNREADABLE_FILE = "unreadable_file"
    MISSING_COLUMNS = "missing_columns"
    EMPTY_FILE = "empty_file"
    EMPTY_CELL = "empty_cell"
    INVALID_NUMBER = "invalid_number"
    DUPLICATE_NUMBER = "duplicate_number"
    DURATION_NOT_POSITIVE = "duration_not_positive"
    INVALID_TYPE = "invalid_type"
    BLOCK_ROW_WITH_EVENT_DATA = "block_row_with_event_data"
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"


class EventNotFound(NotFound, ScheduleException):
    code = "EVENT_NOT_FOUND"


class ScheduleEditTooFast(RateLimited, ScheduleException):
    code = "SCHEDULE_EDIT_TOO_FAST"

    def __init__(self, retry_after: int) -> None:
        super().__init__(details={"retry_after": retry_after})


class CurrentEventNotAllowed(ConstraintViolation, ScheduleException):
    code = "CURRENT_EVENT_NOT_ALLOWED"


class SkippedEventNotAllowed(ConstraintViolation, ScheduleException):
    code = "SKIPPED_EVENT_NOT_ALLOWED"


class SameEventsAreNotAllowed(ConstraintViolation, ScheduleException):
    code = "SAME_EVENTS_ARE_NOT_ALLOWED"


class ScheduleChangeNotFound(NotFound, ScheduleException):
    code = "SCHEDULE_CHANGE_NOT_FOUND"


class OutdatedScheduleChange(Conflict, ScheduleException):
    code = "OUTDATED_SCHEDULE_CHANGE"


class InvalidScheduleFile(ConstraintViolation, ScheduleException):
    """An uploaded schedule spreadsheet cannot be turned into schedule entries.

    `reason` names what is wrong and the remaining details locate it, so the
    frontend can build copy that points at a column and a spreadsheet row
    instead of the generic "file is broken".
    """

    code = "INVALID_SCHEDULE_FILE"

    def __init__(
        self,
        reason: InvalidScheduleFileReason,
        *,
        columns: list[str] | None = None,
        column: str | None = None,
        row: int | None = None,
        number: int | None = None,
    ) -> None:
        details: dict[str, Any] = {"reason": reason.value}
        if columns is not None:
            details["columns"] = columns
        if column is not None:
            details["column"] = column
        if row is not None:
            details["row"] = row
        if number is not None:
            details["number"] = number
        super().__init__(details=details)
