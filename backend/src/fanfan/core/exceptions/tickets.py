from fanfan.core.exceptions.base import AppException, Conflict, NotFound


class TicketException(AppException):
    pass


class TicketNotFound(NotFound, TicketException):
    code = "TICKET_NOT_FOUND"


class UserAlreadyHasTicketLinked(Conflict, TicketException):
    code = "USER_ALREADY_HAS_TICKET_LINKED"


class TicketAlreadyUsed(Conflict, TicketException):
    code = "TICKET_ALREADY_USED"


# The user has no linked ticket: raised when an organiser unlinks one that is
# already gone. Conflict (precondition not met), so 409.
class TicketNotLinked(Conflict, TicketException):
    code = "TICKET_NOT_LINKED"


# Raised when a generated barcode happens to already exist. The unique DB
# constraint is the race-safe guard; this turns that collision into a clean 409
# ("just try again") instead of a leaked 500. Practically never happens.
class TicketBarcodeCollision(Conflict, TicketException):
    code = "TICKET_BARCODE_COLLISION"
