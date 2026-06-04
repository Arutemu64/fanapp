from fanfan.core.exceptions.base import AppException


class SubscriptionException(AppException):
    pass


class SubscriptionAlreadyExists(SubscriptionException):
    code = "SUBSCRIPTION_ALREADY_EXISTS"


class SubscriptionNotFound(SubscriptionException):
    code = "SUBSCRIPTION_NOT_FOUND"
