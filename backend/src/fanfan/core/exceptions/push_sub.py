from fanfan.core.exceptions.base import AppException


class PushSubscriptionException(AppException):
    pass


class PushSubscriptionAlreadyExists(PushSubscriptionException):
    code = "PUSH_SUBSCRIPTION_ALREADY_EXISTS"


class PushSubscriptionNotFound(PushSubscriptionException):
    code = "PUSH_SUBSCRIPTION_NOT_FOUND"
