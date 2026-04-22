from fanfan.core.exceptions.base import AppException


class TicketsException(AppException):
    pass


class TicketNotFound(TicketsException):
    code = "TICKET_NOT_FOUND"


class UserAlreadyHasTicketLinked(TicketsException):
    code = "USER_ALREADY_HAS_TICKET_LINKED"


class TicketAlreadyUsed(TicketsException):
    code = "TICKET_ALREADY_USED"


class TicketNotLinked(TicketsException):
    code = "TICKET_NOT_LINKED"
