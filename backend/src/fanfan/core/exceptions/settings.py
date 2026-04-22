from fanfan.core.exceptions.base import AppException


class AppSettingsException(AppException):
    pass


class AppAppSettingsNotFound(AppSettingsException):
    code = "APP_SETTINGS_NOT_FOUND"
