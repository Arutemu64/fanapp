from fanfan.core.exceptions.base import AppException


class PushSubException(AppException):
    pass


class PushSubscriptionAlreadyExists(PushSubException):
    default_message = "Это устройство уже подписано на push-уведомления"


class PushSubNotFound(PushSubException):
    pass
