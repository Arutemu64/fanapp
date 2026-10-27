from fanfan.core.exceptions.base import (
    AccessDenied,
    AppException,
    Conflict,
    ConstraintViolation,
    NotFound,
)


class QuestException(AppException):
    pass


class QuestDisabled(AccessDenied, QuestException):
    code = "QUEST_DISABLED"


class QuestAwardNotFound(NotFound, QuestException):
    code = "QUEST_AWARD_NOT_FOUND"


class QuestAwardAlreadyExists(Conflict, QuestException):
    code = "QUEST_AWARD_ALREADY_EXISTS"


class QuestAwardAmountOutOfRange(ConstraintViolation, QuestException):
    code = "QUEST_AWARD_AMOUNT_OUT_OF_RANGE"


class CannotAwardSelf(ConstraintViolation, QuestException):
    code = "CANNOT_AWARD_SELF"


class QuestAwardAlreadyCancelled(Conflict, QuestException):
    code = "QUEST_AWARD_ALREADY_CANCELLED"


class QuestAwardCancelWindowExpired(Conflict, QuestException):
    code = "QUEST_AWARD_CANCEL_WINDOW_EXPIRED"
