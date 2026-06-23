from fanfan.core.exceptions.base import (
    AppException,
    Conflict,
    ConstraintViolation,
    NotFound,
)


class UserException(AppException):
    pass


class UserNotFound(NotFound, UserException):
    code = "USER_NOT_FOUND"


class UserAlreadyExists(Conflict, UserException):
    code = "USER_ALREADY_EXISTS"


class UsernameAlreadyTaken(Conflict, UserException):
    code = "USERNAME_ALREADY_TAKEN"


class UsernameProfanity(ConstraintViolation, UserException):
    code = "USERNAME_PROFANITY"


class UserHasNoEmail(Conflict, UserException):
    code = "USER_HAS_NO_EMAIL"


class EmailAlreadyExists(Conflict, UserException):
    code = "EMAIL_ALREADY_EXISTS"


class InvalidEmail(ConstraintViolation, UserException):
    code = "INVALID_EMAIL"


class TelegramAlreadyLinkedToAnotherUser(Conflict, UserException):
    code = "TELEGRAM_ALREADY_LINKED_TO_ANOTHER_USER"


class UserAlreadyHasTelegramLinked(Conflict, UserException):
    code = "USER_ALREADY_HAS_TELEGRAM_LINKED"


class TelegramCannotBeUnlinkedWithoutEmail(Conflict, UserException):
    code = "TELEGRAM_CANNOT_BE_UNLINKED_WITHOUT_EMAIL"
