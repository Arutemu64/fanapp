from fanfan.core.exceptions.base import AppException


class VoteException(AppException):
    pass


class VoteAlreadyExists(VoteException):
    code = "ALREADY_VOTED_IN_THIS_NOMINATION"


class VoteNotFound(VoteException):
    code = "VOTE_NOT_FOUND"
