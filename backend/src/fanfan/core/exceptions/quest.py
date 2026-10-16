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
    # The feature flag in app settings is off: the quest card and tool are
    # hidden, and every quest endpoint refuses rather than half-working.
    code = "QUEST_DISABLED"


class QuestAwardNotFound(NotFound, QuestException):
    code = "QUEST_AWARD_NOT_FOUND"


class QuestAwardAlreadyExists(Conflict, QuestException):
    # The client-chosen award ID is taken by a different award. A replay of
    # the same award is not an error (docs/adr/0034).
    code = "QUEST_AWARD_ALREADY_EXISTS"


class QuestAwardAmountOutOfRange(ConstraintViolation, QuestException):
    code = "QUEST_AWARD_AMOUNT_OUT_OF_RANGE"


class CannotAwardSelf(ConstraintViolation, QuestException):
    # Staff earn points too, so nothing but this check stops a volunteer from
    # topping up their own balance.
    code = "CANNOT_AWARD_SELF"


class QuestAwardAlreadyCancelled(Conflict, QuestException):
    code = "QUEST_AWARD_ALREADY_CANCELLED"


class QuestAwardCancelWindowExpired(Conflict, QuestException):
    code = "QUEST_AWARD_CANCEL_WINDOW_EXPIRED"
