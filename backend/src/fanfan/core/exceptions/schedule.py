from fanfan.core.exceptions.base import (
    AppException,
    Conflict,
    ConstraintViolation,
    NotFound,
    RateLimited,
)


class ScheduleException(AppException):
    pass


class ScheduleItemNotFound(NotFound, ScheduleException):
    code = "SCHEDULE_ITEM_NOT_FOUND"


class ScheduleEditTooFast(RateLimited, ScheduleException):
    code = "SCHEDULE_EDIT_TOO_FAST"

    def __init__(self, retry_after: int) -> None:
        super().__init__(details={"retry_after": retry_after})


class CurrentScheduleItemNotAllowed(ConstraintViolation, ScheduleException):
    code = "CURRENT_SCHEDULE_ITEM_NOT_ALLOWED"


class SkippedScheduleItemNotAllowed(ConstraintViolation, ScheduleException):
    code = "SKIPPED_SCHEDULE_ITEM_NOT_ALLOWED"


class SameScheduleItemsAreNotAllowed(ConstraintViolation, ScheduleException):
    code = "SAME_SCHEDULE_ITEMS_ARE_NOT_ALLOWED"


class ScheduleChangeNotFound(NotFound, ScheduleException):
    code = "SCHEDULE_CHANGE_NOT_FOUND"


class OutdatedScheduleChange(Conflict, ScheduleException):
    code = "OUTDATED_SCHEDULE_CHANGE"
