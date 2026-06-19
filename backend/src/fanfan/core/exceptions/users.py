from fanfan.core.exceptions.base import AppException


class UserException(AppException):
    pass


class UserNotFound(UserException):
    code = "USER_NOT_FOUND"


class UserAlreadyExists(UserException):
    code = "USER_ALREADY_EXISTS"


class UsernameAlreadyTaken(UserException):
    code = "USERNAME_ALREADY_TAKEN"


class UsernameProfanity(UserException):
    code = "USERNAME_PROFANITY"


class UserHasNoEmail(UserException):
    code = "USER_HAS_NO_EMAIL"


class EmailAlreadyExists(UserException):
    code = "EMAIL_ALREADY_EXISTS"


class InvalidEmail(UserException):
    code = "INVALID_EMAIL"


class TelegramAlreadyLinkedToAnotherUser(UserException):
    code = "TELEGRAM_ALREADY_LINKED_TO_ANOTHER_USER"


class UserAlreadyHasTelegramLinked(UserException):
    code = "USER_ALREADY_HAS_TELEGRAM_LINKED"


class TelegramCannotBeUnlinkedWithoutEmail(UserException):
    code = "TELEGRAM_CANNOT_BE_UNLINKED_WITHOUT_EMAIL"
