from fanfan.core.exceptions.base import AppException, Conflict


class SyncException(AppException):
    pass


class SyncAlreadyRunning(Conflict, SyncException):
    code = "SYNC_ALREADY_RUNNING"
