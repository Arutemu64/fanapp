from fanfan.core.exceptions.base import AppException


class NominationsException(AppException):
    pass


class NominationNotFound(NominationsException):
    code = "NOMINATION_NOT_FOUND"
