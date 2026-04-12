from fanfan.core.exceptions.base import AppException


class AppSettingsException(AppException):
    pass


class AppAppSettingsNotFound(AppSettingsException):
    pass
