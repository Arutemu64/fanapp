from fanfan.core.exceptions.base import AppException, Conflict, NotFound


class TicketException(AppException):
    pass


class TicketNotFound(NotFound, TicketException):
    code = "TICKET_NOT_FOUND"


class UserAlreadyHasTicketLinked(Conflict, TicketException):
    code = "USER_ALREADY_HAS_TICKET_LINKED"


class TicketAlreadyUsed(Conflict, TicketException):
    code = "TICKET_ALREADY_USED"


# Not raised by the backend yet, but the frontend already maps its code; mark it
# Conflict (precondition not met) so it returns 409, not 500, once it is used.
class TicketNotLinked(Conflict, TicketException):
    code = "TICKET_NOT_LINKED"


# Raised when a generated barcode happens to already exist. The unique DB
# constraint is the race-safe guard; this turns that collision into a clean 409
# ("just try again") instead of a leaked 500. Practically never happens.
class TicketBarcodeCollision(Conflict, TicketException):
    code = "TICKET_BARCODE_COLLISION"
