from fanfan.core.exceptions.base import AppException


class NominationException(AppException):
    pass


class NominationNotFound(NominationException):
    code = "NOMINATION_NOT_FOUND"
