from fanfan.core.exceptions.base import AppException


class Cosplay2Exception(AppException):
    pass


class NoCosplay2ConfigProvided(Cosplay2Exception):
    code = "COSPLAY2_CONFIG_NOT_PROVIDED"
