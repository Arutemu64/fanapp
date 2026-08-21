from fanfan.core.exceptions.base import AppException, UpstreamServiceError


class EmailException(AppException):
    pass


class EmailDeliveryFailed(UpstreamServiceError, EmailException):
    """The mail relay could not be reached or refused the message.

    Raised by the email-sender adapter when SMTP delivery fails (connection
    dropped, timeout, auth or recipient rejection). The login-code flow sends
    synchronously so the caller learns the code never went out; surfacing this as
    a domain error (502) instead of an unhandled 500 gives the user an actionable
    "try again" message and stops a mail outage from spamming error tracking.
    """

    code = "EMAIL_DELIVERY_FAILED"
