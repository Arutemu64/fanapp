from fanfan.core.exceptions.base import (
    AppException,
    Conflict,
    ConstraintViolation,
    NotFound,
    RateLimited,
)


class ScheduleException(AppException):
    pass


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
