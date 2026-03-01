from fanfan.core.exceptions.base import AppException


class NotificationsException(AppException):
    pass


class NotificationNotFound(NotificationsException):
    default_message = "Уведомление не найдено"


class MailingNotFound(NotificationsException):
    default_message = "Рассылка не найдена"


class MailingCancelled(NotificationsException):
    default_message = "Рассылка отменена"


class UserNotReachable(NotificationsException):
    default_message = "Пользователю нельзя отправить сообщение"


class NotificationRetryAfter(NotificationsException):
    default_message = "Попробуйте отправку позже"

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
