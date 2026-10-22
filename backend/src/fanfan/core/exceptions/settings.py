from fanfan.core.exceptions.base import (
    AppException,
    ConstraintViolation,
    NotFound,
    PreconditionFailed,
)


class AppSettingsException(AppException):
    pass


class AppSettingsNotFound(NotFound, AppSettingsException):
    code = "APP_SETTINGS_NOT_FOUND"


class InvalidVotingTimeRange(ConstraintViolation, AppSettingsException):
    code = "INVALID_VOTING_TIME_RANGE"


class InvalidFestivalTimeRange(ConstraintViolation, AppSettingsException):
    code = "INVALID_FESTIVAL_TIME_RANGE"


class InvalidTCloudEventId(ConstraintViolation, AppSettingsException):
    code = "INVALID_TCLOUD_EVENT_ID"


class AppSettingsChanged(PreconditionFailed, AppSettingsException):
    code = "APP_SETTINGS_CHANGED"


class TCloudEventRolesChanged(PreconditionFailed, AppSettingsException):
    code = "TCLOUD_EVENT_ROLES_CHANGED"
