from fanfan.core.exceptions.base import AppException, NotFound


class ParticipantException(AppException):
    pass


class ParticipantNotFound(NotFound, ParticipantException):
    code = "PARTICIPANT_NOT_FOUND"
