from fanfan.core.exceptions.base import AppException


class ScheduleException(AppException):
    pass


class EventNotFound(ScheduleException):
    code = "EVENT_NOT_FOUND"


class ScheduleEditTooFast(ScheduleException):
    code = "SCHEDULE_EDIT_TOO_FAST"

    def __init__(self, retry_after: int) -> None:
        super().__init__(details={"retry_after": retry_after})


class CurrentEventNotAllowed(ScheduleException):
    code = "CURRENT_EVENT_NOT_ALLOWED"


class SkippedEventNotAllowed(ScheduleException):
    code = "SKIPPED_EVENT_NOT_ALLOWED"


class SameEventsAreNotAllowed(ScheduleException):
    code = "SAME_EVENTS_ARE_NOT_ALLOWED"


class ScheduleChangeNotFound(ScheduleException):
    code = "SCHEDULE_CHANGE_NOT_FOUND"


class OutdatedScheduleChange(ScheduleException):
    code = "OUTDATED_SCHEDULE_CHANGE"
