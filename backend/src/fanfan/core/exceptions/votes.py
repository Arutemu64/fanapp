from fanfan.core.exceptions.base import AppException, Conflict, NotFound


class VoteException(AppException):
    pass


class VoteAlreadyExists(Conflict, VoteException):
    code = "ALREADY_VOTED_IN_THIS_NOMINATION"


class VoteNotFound(NotFound, VoteException):
    code = "VOTE_NOT_FOUND"
