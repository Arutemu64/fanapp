from fanfan.core.exceptions.base import AppException


class ParticipantException(AppException):
    pass


class ParticipantNotFound(ParticipantException):
    code = "PARTICIPANT_NOT_FOUND"
