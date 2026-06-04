from fanfan.core.exceptions.base import AppException


class ParticipantException(AppException):
    pass


class ParticipantNotFound(ParticipantException):
    code = "PARTICIPANT_NOT_FOUND"


class NonApprovedRequest(ParticipantException):
    code = "NON_APPROVED_REQUEST"


class RequestHasNoVotingTitle(ParticipantException):
    code = "REQUEST_HAS_NO_VOTING_TITLE"
