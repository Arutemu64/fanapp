from fanfan.core.exceptions.base import AppException


class TicketException(AppException):
    pass


class TicketNotFound(TicketException):
    code = "TICKET_NOT_FOUND"


class UserAlreadyHasTicketLinked(TicketException):
    code = "USER_ALREADY_HAS_TICKET_LINKED"


class TicketAlreadyUsed(TicketException):
    code = "TICKET_ALREADY_USED"


class TicketNotLinked(TicketException):
    code = "TICKET_NOT_LINKED"
