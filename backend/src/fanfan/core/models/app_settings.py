from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from fanfan.core.exceptions.quest import QuestDisabled
from fanfan.core.exceptions.settings import (
    InvalidFestivalTimeRange,
    InvalidTCloudEventId,
    InvalidVotingTimeRange,
)
from fanfan.core.models.base import AggregateRoot
from fanfan.core.vo.user import UserRole

DEFAULT_FESTIVAL_START = datetime(
    2027, 3, 13, 11, 30, tzinfo=timezone(timedelta(hours=3))
)
DEFAULT_FESTIVAL_END = datetime(
    2027, 3, 13, 19, 30, tzinfo=timezone(timedelta(hours=3))
)


@dataclass(slots=True, kw_only=True)
class LimitsConfig:
    announcement_cooldown_seconds: int = 10


@dataclass(slots=True, kw_only=True)
class QuestConfig:
    enabled: bool = False
    max_award: int = 100
    cancel_window_minutes: int = 15


@dataclass(slots=True, kw_only=True)
class ScheduleConfig:
    changeover_seconds: int = 30


@dataclass(slots=True, kw_only=True)
class TicketsConfig:
    tcloud_event_roles: dict[str, UserRole] = field(default_factory=dict)

    def role_for_tcloud_event(self, event_id: str) -> UserRole:
        return self.tcloud_event_roles.get(event_id, UserRole.VISITOR)


@dataclass(slots=True, kw_only=True)
class AppSettings(AggregateRoot):
    voting_start: datetime | None = None
    voting_end: datetime | None = None

    festival_start: datetime = DEFAULT_FESTIVAL_START
    festival_end: datetime = DEFAULT_FESTIVAL_END

    limits: LimitsConfig = field(default_factory=LimitsConfig)
    quest: QuestConfig = field(default_factory=QuestConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    tickets: TicketsConfig = field(default_factory=TicketsConfig)

    def set_voting_time_range(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> None:
        if (start is None) != (end is None):
            raise InvalidVotingTimeRange
        if start is not None and end is not None and end <= start:
            raise InvalidVotingTimeRange
        self.voting_start = start
        self.voting_end = end

    def is_voting_open(self, *, now: datetime) -> bool:
        if self.voting_start is None or self.voting_end is None:
            return False
        return self.voting_start <= now < self.voting_end

    def set_festival_schedule(self, *, start: datetime, end: datetime) -> None:
        if end <= start:
            raise InvalidFestivalTimeRange
        self.festival_start = start
        self.festival_end = end

    def update_limits(
        self,
        *,
        announcement_cooldown_seconds: int | None = None,
    ) -> None:
        if announcement_cooldown_seconds is not None:
            self.limits.announcement_cooldown_seconds = announcement_cooldown_seconds

    def update_schedule(self, *, changeover_seconds: int | None = None) -> None:
        if changeover_seconds is not None:
            self.schedule.changeover_seconds = changeover_seconds

    def ensure_quest_enabled(self) -> None:
        if not self.quest.enabled:
            raise QuestDisabled

    def update_quest(
        self,
        *,
        enabled: bool | None = None,
        max_award: int | None = None,
        cancel_window_minutes: int | None = None,
    ) -> None:
        if enabled is not None:
            self.quest.enabled = enabled
        if max_award is not None:
            self.quest.max_award = max_award
        if cancel_window_minutes is not None:
            self.quest.cancel_window_minutes = cancel_window_minutes

    def set_tcloud_event_roles(self, event_roles: dict[str, UserRole]) -> None:
        cleaned: dict[str, UserRole] = {}
        for event_id, role in event_roles.items():
            key = event_id.strip()
            if not key:
                raise InvalidTCloudEventId
            cleaned[key] = role
        self.tickets.tcloud_event_roles = cleaned
