import time

from fanfan.core.exceptions.base import AppException
from fanfan.core.utils.pluralize import SECONDS_PLURALS, pluralize
from fanfan.core.vo.schedule_event import ScheduleEventId


class ScheduleException(AppException):
    pass


class EventNotFound(ScheduleException):
    default_message = "Выступление не найдено"

    def __init__(self, event_id: ScheduleEventId | None = None) -> None:
        if isinstance(event_id, int):
            self.message = f"Выступление {event_id} не найдено"


class ScheduleEditTooFast(ScheduleException):
    def __init__(self, announcement_timeout: float, old_timestamp: float) -> None:
        self.retry_after = int(old_timestamp + announcement_timeout - time.time())
        self.message = (
            f"С последнего изменения расписания "
            f"не прошло {int(announcement_timeout)} "
            f"{pluralize(int(announcement_timeout), SECONDS_PLURALS)}! "
            f"Попробуйте ещё раз через "
            f"{self.retry_after} {pluralize(self.retry_after, SECONDS_PLURALS)}."
        )


class CurrentEventNotAllowed(ScheduleException):
    default_message = "Это выступление является текущим"


class SkippedEventNotAllowed(ScheduleException):
    default_message = "Текущее выступление не может быть пропущенным"


class SameEventsAreNotAllowed(ScheduleException):
    default_message = "Выступления не могут совпадать"


class ScheduleChangeNotFound(ScheduleException):
    default_message = "Изменение расписания не найдено. Возможно, оно отменено."


class OutdatedScheduleChange(ScheduleException):
    default_message = "Это изменение уже неактуально."
