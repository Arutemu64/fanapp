from fanfan.core.exceptions.base import AppException


class NotificationException(AppException):
    pass


class NotificationNotFound(NotificationException):
    code = "NOTIFICATION_NOT_FOUND"


class MailingNotFound(NotificationException):
    code = "MAILING_NOT_FOUND"


class MailingAlreadyCancelled(NotificationException):
    code = "MAILING_CANCELLED"


class UserNotReachable(NotificationException):
    code = "USER_NOT_REACHABLE"


class NotificationRetryAfter(NotificationException):
    code = "NOTIFICATION_RETRY_AFTER"

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(details={"retry_after": retry_after})
