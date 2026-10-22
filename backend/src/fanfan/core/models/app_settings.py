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

# Programme opening and close, Moscow time (UTC+3). The defaults the app ships
# with until organizers override them from the settings page; together they
# drive the home-page countdown and the before/during/after phase boundaries.
DEFAULT_FESTIVAL_START = datetime(
    2027, 3, 13, 11, 30, tzinfo=timezone(timedelta(hours=3))
)
DEFAULT_FESTIVAL_END = datetime(
    2027, 3, 13, 19, 30, tzinfo=timezone(timedelta(hours=3))
)


@dataclass(slots=True, kw_only=True)
class LimitsConfig:
    announcement_timeout: int = 10


@dataclass(slots=True, kw_only=True)
class QuestConfig:
    # Off by default: the quest runs only at festivals that hand out merch for it.
    enabled: bool = False
    # Caps one award so a typo (1000 for 10) cannot top the leaderboard.
    max_award: int = 100
    # How long a volunteer may cancel their own award; organizers holding
    # quest:manage cancel at any time.
    cancel_window_minutes: int = 15


@dataclass(slots=True, kw_only=True)
class ScheduleConfig:
    # The pause between two acts while one group leaves and the next walks on,
    # which the planned durations leave out. Added once per act to the wait
    # estimate (ADR-0043). The default is a guess until a festival's
    # set-as-current log measures it.
    changeover_seconds: int = 30


@dataclass(slots=True, kw_only=True)
class TicketsConfig:
    # TicketsCloud event id → the role its buyers get. Organizers edit it from
    # the tickets tool; an event left out sells visitor tickets.
    tcloud_event_roles: dict[str, UserRole] = field(default_factory=dict)

    def role_for_tcloud_event(self, event_id: str) -> UserRole:
        return self.tcloud_event_roles.get(event_id, UserRole.VISITOR)


@dataclass(slots=True, kw_only=True)
class AppSettings(AggregateRoot):
    # Voting is open when ``now`` falls within [voting_start, voting_end).
    # Both None means voting is closed (the default).
    voting_start: datetime | None = None
    voting_end: datetime | None = None

    festival_start: datetime = DEFAULT_FESTIVAL_START
    # The festival is over once ``now`` reaches this instant — the home page
    # flips to the wrap-up "after" phase on its own. Organizers move it forward
    # from the settings page when an act runs long, rather than flipping a switch.
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
        # The home page derives its before/during/after phase from this range, so
        # an end at or before the start would erase the "during" phase and jump the
        # countdown straight to the farewell. The two instants can be PATCHed
        # independently and no other layer guards their order, so the aggregate
        # enforces it — the same shape as set_voting_time_range above.
        if end <= start:
            raise InvalidFestivalTimeRange
        self.festival_start = start
        self.festival_end = end

    def update_limits(
        self,
        *,
        announcement_timeout: int | None = None,
    ) -> None:
        # Mutation of the nested limits config goes through the aggregate root
        # so callers never reach into it directly. None means "leave as is".
        if announcement_timeout is not None:
            self.limits.announcement_timeout = announcement_timeout

    def update_schedule(self, *, changeover_seconds: int | None = None) -> None:
        # None means "leave as is", like update_limits.
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
        # None means "leave as is", like update_limits.
        if enabled is not None:
            self.quest.enabled = enabled
        if max_award is not None:
            self.quest.max_award = max_award
        if cancel_window_minutes is not None:
            self.quest.cancel_window_minutes = cancel_window_minutes

    def set_tcloud_event_roles(self, event_roles: dict[str, UserRole]) -> None:
        # Replaces the whole mapping: the form edits it as one list, so a row
        # removed there must disappear here too.
        cleaned: dict[str, UserRole] = {}
        for event_id, role in event_roles.items():
            key = event_id.strip()
            if not key:
                raise InvalidTCloudEventId
            cleaned[key] = role
        self.tickets.tcloud_event_roles = cleaned
