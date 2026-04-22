from fanfan.core.exceptions.base import AppException


class ParticipantsException(AppException):
    pass


class ParticipantNotFound(ParticipantsException):
    code = "PARTICIPANT_NOT_FOUND"


class NonApprovedRequest(ParticipantsException):
    code = "NON_APPROVED_REQUEST"


class RequestHasNoVotingTitle(ParticipantsException):
    code = "REQUEST_HAS_NO_VOTING_TITLE"
