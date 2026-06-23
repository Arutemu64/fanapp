from fanfan.core.exceptions.base import AppException, NotFound


class AppSettingsException(AppException):
    pass


class AppSettingsNotFound(NotFound, AppSettingsException):
    code = "APP_SETTINGS_NOT_FOUND"
