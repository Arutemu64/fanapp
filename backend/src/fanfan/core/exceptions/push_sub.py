from fanfan.core.exceptions.base import AppException, Conflict, NotFound


class PushSubscriptionException(AppException):
    pass


class PushSubscriptionAlreadyExists(Conflict, PushSubscriptionException):
    code = "PUSH_SUBSCRIPTION_ALREADY_EXISTS"


class PushSubscriptionNotFound(NotFound, PushSubscriptionException):
    code = "PUSH_SUBSCRIPTION_NOT_FOUND"
