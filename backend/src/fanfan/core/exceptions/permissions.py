from fanfan.core.exceptions.base import AppException


class PermissionException(AppException):
    pass


class PermissionNotFound(PermissionException):
    code = "PERMISSION_NOT_FOUND"


class UserAlreadyHasPermission(PermissionException):
    code = "USER_ALREADY_HAS_PERMISSION"
