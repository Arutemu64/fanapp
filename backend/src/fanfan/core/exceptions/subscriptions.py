from fanfan.core.exceptions.base import AppException


class SubscriptionsException(AppException):
    pass


class SubscriptionAlreadyExist(SubscriptionsException):
    code = "SUBSCRIPTION_ALREADY_EXISTS"


class SubscriptionNotFound(SubscriptionsException):
    code = "SUBSCRIPTION_NOT_FOUND"
