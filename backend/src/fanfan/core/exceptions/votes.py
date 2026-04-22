from fanfan.core.exceptions.base import AppException


class VotesException(AppException):
    pass


class AlreadyVotedInThisNomination(VotesException):
    code = "ALREADY_VOTED_IN_THIS_NOMINATION"


class VoteNotFound(VotesException):
    code = "VOTE_NOT_FOUND"
