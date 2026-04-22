from fanfan.core.exceptions.base import AppException


class PermissionsException(AppException):
    pass


class PermissionNotFound(PermissionsException):
    code = "PERMISSION_NOT_FOUND"


class UserAlreadyHasPermission(PermissionsException):
    code = "USER_ALREADY_HAS_PERMISSION"
