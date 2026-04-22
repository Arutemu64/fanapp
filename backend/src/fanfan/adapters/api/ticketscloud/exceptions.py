from fanfan.core.exceptions.base import AppException


class TCloudException(AppException):
    pass


class NoTCloudConfigProvided(TCloudException):
    code = "TCLOUD_CONFIG_NOT_PROVIDED"
