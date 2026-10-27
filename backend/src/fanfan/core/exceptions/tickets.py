from fanfan.core.exceptions.base import AppException, Conflict, NotFound


class TicketException(AppException):
    pass


class TicketNotFound(NotFound, TicketException):
    code = "TICKET_NOT_FOUND"


class UserAlreadyHasTicketLinked(Conflict, TicketException):
    code = "USER_ALREADY_HAS_TICKET_LINKED"


class TicketAlreadyUsed(Conflict, TicketException):
    code = "TICKET_ALREADY_USED"


class TicketRevoked(Conflict, TicketException):
    code = "TICKET_REVOKED"


class TicketNotLinked(Conflict, TicketException):
    code = "TICKET_NOT_LINKED"


class TicketBatchAlreadyExists(Conflict, TicketException):
    code = "TICKET_BATCH_ALREADY_EXISTS"
