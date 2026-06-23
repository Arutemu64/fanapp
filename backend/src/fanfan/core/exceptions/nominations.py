from fanfan.core.exceptions.base import AppException, NotFound


class NominationException(AppException):
    pass


class NominationNotFound(NotFound, NominationException):
    code = "NOMINATION_NOT_FOUND"
