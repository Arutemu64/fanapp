from fanfan.core.exceptions.base import AppException, Conflict, NotFound


class NotificationException(AppException):
    pass


class NotificationNotFound(NotificationException):
    code = "NOTIFICATION_NOT_FOUND"


# Markers first so they win MRO precedence: these three are raised from the
# CancelMailing HTTP command (as well as the NATS consumers), so they must
# resolve to real 4xx statuses rather than the internal-only 500.
class MailingNotFound(NotFound, NotificationException):
    code = "MAILING_NOT_FOUND"


class MailingAlreadyCancelled(Conflict, NotificationException):
    code = "MAILING_CANCELLED"


class MailingNotCancellable(Conflict, NotificationException):
    # The mailing already reached a terminal non-cancelled state (finished or
    # failed), so there is nothing left to cancel.
    code = "MAILING_NOT_CANCELLABLE"


class UserNotReachable(NotificationException):
    code = "USER_NOT_REACHABLE"


class NotificationChannelUnavailable(NotificationException):
    # A whole delivery channel is misconfigured (e.g. missing/invalid VAPID
    # keys), as opposed to a single user being unreachable. Consumers should
    # drop the message rather than retry — retrying can't fix a config error.
    code = "NOTIFICATION_CHANNEL_UNAVAILABLE"


class NotificationRetryAfter(NotificationException):
    code = "NOTIFICATION_RETRY_AFTER"

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(details={"retry_after": retry_after})
