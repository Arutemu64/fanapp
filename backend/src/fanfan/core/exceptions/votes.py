from fanfan.core.exceptions.base import AccessDenied, AppException, Conflict, NotFound


class VoteException(AppException):
    pass


class VoteAlreadyExists(Conflict, VoteException):
    code = "ALREADY_VOTED_IN_THIS_NOMINATION"


class VoteNotFound(NotFound, VoteException):
    code = "VOTE_NOT_FOUND"


class VotingTicketRequired(AccessDenied, VoteException):
    code = "VOTING_TICKET_REQUIRED"


class VotingDisabled(AccessDenied, VoteException):
    code = "VOTING_DISABLED"
