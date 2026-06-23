from fanfan.core.exceptions.base import AppException, Conflict, NotFound


class SubscriptionException(AppException):
    pass


class SubscriptionAlreadyExists(Conflict, SubscriptionException):
    code = "SUBSCRIPTION_ALREADY_EXISTS"


class SubscriptionNotFound(NotFound, SubscriptionException):
    code = "SUBSCRIPTION_NOT_FOUND"
