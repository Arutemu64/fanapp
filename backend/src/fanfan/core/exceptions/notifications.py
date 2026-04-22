from fanfan.core.exceptions.base import AppException


class NotificationsException(AppException):
    pass


class NotificationNotFound(NotificationsException):
    code = "NOTIFICATION_NOT_FOUND"


class MailingNotFound(NotificationsException):
    code = "MAILING_NOT_FOUND"


class MailingCancelled(NotificationsException):
    code = "MAILING_CANCELLED"


class UserNotReachable(NotificationsException):
    code = "USER_NOT_REACHABLE"


class NotificationRetryAfter(NotificationsException):
    code = "NOTIFICATION_RETRY_AFTER"

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(details={"retry_after": retry_after})
