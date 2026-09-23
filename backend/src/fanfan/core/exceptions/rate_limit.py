from fanfan.core.exceptions.base import AppException, RateLimited


class RateLimitException(AppException):
    pass


# Internal: a caller catches this and re-raises a flow-specific RateLimited
# exception (below), so the cooldown guard never reaches the HTTP boundary and
# intentionally carries no status marker.
class CooldownActive(RateLimitException):
    code = "COOLDOWN_ACTIVE"

    def __init__(self, retry_after: int) -> None:
        super().__init__(details={"retry_after": retry_after})


class EmailCodeRequestTooFast(RateLimited, RateLimitException):
    code = "EMAIL_CODE_REQUEST_TOO_FAST"

    def __init__(self, retry_after: int) -> None:
        super().__init__(details={"retry_after": retry_after})


class TooManyAttempts(RateLimited, RateLimitException):
    """Raised by the RateLimiter port when a key goes over its attempt limit.

    Callers catch this and re-raise a flow-specific subclass so each feature can
    keep its own error code and Russian copy.
    """

    code = "TOO_MANY_ATTEMPTS"

    def __init__(self, retry_after: int) -> None:
        super().__init__(details={"retry_after": retry_after})


class TooManyOtpAttempts(TooManyAttempts):
    code = "TOO_MANY_OTP_ATTEMPTS"


class TooManyLoginAttempts(TooManyAttempts):
    code = "TOO_MANY_LOGIN_ATTEMPTS"
