from fanfan.core.exceptions.base import AccessDenied, AppException, NotFound


class NominationException(AppException):
    pass


class NominationNotFound(NotFound, NominationException):
    code = "NOMINATION_NOT_FOUND"


class NominationNotVotable(AccessDenied, NominationException):
    code = "NOMINATION_NOT_VOTABLE"
