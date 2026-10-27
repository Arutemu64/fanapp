from fanfan.core.exceptions.base import AppException, Conflict, NotFound, RateLimited


class NotificationException(AppException):
    pass


class NotificationNotFound(NotificationException):
    code = "NOTIFICATION_NOT_FOUND"


class MailingNotFound(NotFound, NotificationException):
    code = "MAILING_NOT_FOUND"


class MailingAlreadyCancelled(Conflict, NotificationException):
    code = "MAILING_CANCELLED"


class MailingAlreadyExists(Conflict, NotificationException):
    code = "MAILING_ALREADY_EXISTS"


class TestNotificationTooFast(RateLimited, NotificationException):
    code = "TEST_NOTIFICATION_TOO_FAST"

    def __init__(self, retry_after: int) -> None:
        super().__init__(details={"retry_after": retry_after})


class UserNotReachable(NotificationException):
    code = "USER_NOT_REACHABLE"


class NotificationChannelUnavailable(NotificationException):
    code = "NOTIFICATION_CHANNEL_UNAVAILABLE"


class NotificationExpired(NotificationException):
    code = "NOTIFICATION_EXPIRED"


class NotificationSuperseded(NotificationException):
    code = "NOTIFICATION_SUPERSEDED"


class NotificationRetryAfter(NotificationException):
    code = "NOTIFICATION_RETRY_AFTER"

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(details={"retry_after": retry_after})
