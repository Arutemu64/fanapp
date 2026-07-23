from fanfan.core.exceptions.base import AppException, RateLimited


class SyncException(AppException):
    pass


class SyncAlreadyRunning(RateLimited, SyncException):
    code = "SYNC_ALREADY_RUNNING"


class SyncTooFast(RateLimited, SyncException):
    code = "SYNC_TOO_FAST"

    def __init__(self, retry_after: int):
        super().__init__(details={"retry_after": retry_after})
