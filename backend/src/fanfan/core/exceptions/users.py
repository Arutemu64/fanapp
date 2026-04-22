from fanfan.core.exceptions.base import AppException


class UsersException(AppException):
    pass


class UserNotFound(UsersException):
    code = "USER_NOT_FOUND"


class UserAlreadyExists(UsersException):
    code = "USER_ALREADY_EXISTS"


class UsernameAlreadyTaken(UsersException):
    code = "USERNAME_ALREADY_TAKEN"


class UserHasNoEmail(UsersException):
    code = "USER_HAS_NO_EMAIL"


class EmailAlreadyExists(UsersException):
    code = "EMAIL_ALREADY_EXISTS"


class TelegramAlreadyLinkedToAnotherUser(UsersException):
    code = "TELEGRAM_ALREADY_LINKED_TO_ANOTHER_USER"


class UserAlreadyHasTelegramLinked(UsersException):
    code = "USER_ALREADY_HAS_TELEGRAM_LINKED"


class TelegramCannotBeUnlinkedWithoutEmail(UsersException):
    code = "TELEGRAM_CANNOT_BE_UNLINKED_WITHOUT_EMAIL"
