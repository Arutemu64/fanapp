from fanfan.core.exceptions.base import AppException, Conflict, NotFound, RateLimited


class NotificationException(AppException):
    pass


class NotificationNotFound(NotificationException):
    code = "NOTIFICATION_NOT_FOUND"


# Markers first so they win MRO precedence: these three are raised from the
# CancelMailing HTTP command (as well as the background tasks), so they must
# resolve to real 4xx statuses rather than the internal-only 500.
class MailingNotFound(NotFound, NotificationException):
    code = "MAILING_NOT_FOUND"


class MailingAlreadyCancelled(Conflict, NotificationException):
    code = "MAILING_CANCELLED"


class MailingAlreadyExists(Conflict, NotificationException):
    # The client-chosen mailing ID is taken by a different broadcast: another
    # author, text or audience. A replay of the same broadcast is not an error.
    code = "MAILING_ALREADY_EXISTS"


class MailingNotCancellable(Conflict, NotificationException):
    # The mailing already reached a terminal non-cancelled state (finished or
    # failed), so there is nothing left to cancel.
    code = "MAILING_NOT_CANCELLABLE"


class TestNotificationTooFast(RateLimited, NotificationException):
    code = "TEST_NOTIFICATION_TOO_FAST"

    def __init__(self, retry_after: int) -> None:
        super().__init__(details={"retry_after": retry_after})


class UserNotReachable(NotificationException):
    code = "USER_NOT_REACHABLE"


class NotificationChannelUnavailable(NotificationException):
    # A whole delivery channel is misconfigured (e.g. missing/invalid VAPID
    # keys), as opposed to a single user being unreachable. Consumers should
    # drop the message rather than retry — retrying can't fix a config error.
    code = "NOTIFICATION_CHANNEL_UNAVAILABLE"


class NotificationRetryAfter(NotificationException):
    code = "NOTIFICATION_RETRY_AFTER"

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(details={"retry_after": retry_after})
