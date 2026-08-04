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


class VkAlreadyLinkedToAnotherUser(Conflict, UserException):
    code = "VK_ALREADY_LINKED_TO_ANOTHER_USER"


class UserAlreadyHasVkLinked(Conflict, UserException):
    code = "USER_ALREADY_HAS_VK_LINKED"


class VkCannotBeUnlinkedWithoutEmail(Conflict, UserException):
    code = "VK_CANNOT_BE_UNLINKED_WITHOUT_EMAIL"


class LinkInitiatorMismatch(Conflict, UserException):
    """The session that finished an account link is not the one that started it.

    Raised when the browser signed in as somebody else between the redirect to
    the provider and the callback. Attaching the identity anyway would bind
    someone else's external account to whoever happens to hold the session now,
    so the link is refused rather than retargeted.
    """

    code = "LINK_INITIATOR_MISMATCH"
