from fanfan.core.exceptions.base import AppException


class RateLimitException(AppException):
    pass


class RateLimitCooldown(RateLimitException):
    code = "RATE_LOCK_COOLDOWN"

    def __init__(self, retry_after: int):
        super().__init__(details={"retry_after": retry_after})


class RateLimitInUse(RateLimitException):
    code = "RATE_LOCK_IN_USE"


class EmailCodeRequestTooFast(RateLimitException):
    code = "EMAIL_CODE_REQUEST_TOO_FAST"

    def __init__(self, retry_after: int):
        super().__init__(details={"retry_after": retry_after})


class TooManyOtpAttempts(RateLimitException):
    code = "TOO_MANY_OTP_ATTEMPTS"

    def __init__(self, retry_after: int):
        super().__init__(details={"retry_after": retry_after})
