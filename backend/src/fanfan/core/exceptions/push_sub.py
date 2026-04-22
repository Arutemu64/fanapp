from fanfan.core.exceptions.base import AppException


class PushSubException(AppException):
    pass


class PushSubscriptionAlreadyExists(PushSubException):
    code = "PUSH_SUBSCRIPTION_ALREADY_EXISTS"


class PushSubNotFound(PushSubException):
    code = "PUSH_SUBSCRIPTION_NOT_FOUND"
