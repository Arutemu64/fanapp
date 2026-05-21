import time

from fanfan.core.exceptions.base import AppException


class LimiterException(AppException):
    pass


class RateLockCooldown(LimiterException):
    code = "RATE_LOCK_COOLDOWN"

    def __init__(self, cooldown_period: float, timestamp: float):
        retry_after = max(0, int(timestamp + cooldown_period - time.time()))
        super().__init__(details={"retry_after": retry_after})


class RateLockInUse(LimiterException):
    code = "RATE_LOCK_IN_USE"


class EmailCodeRequestTooFast(LimiterException):
    code = "EMAIL_CODE_REQUEST_TOO_FAST"

    def __init__(self, retry_after: int):
        super().__init__(details={"retry_after": retry_after})
