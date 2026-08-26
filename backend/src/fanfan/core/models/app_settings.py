from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from fanfan.core.exceptions.settings import InvalidVotingTimeRange
from fanfan.core.models.base import AggregateRoot

# Programme opening, Moscow time (UTC+3). The default the app ships with until
# organizers override it from the settings page; it drives the home-page
# countdown and the before/during phase boundary.
DEFAULT_FESTIVAL_START = datetime(
    2026, 8, 22, 11, 30, tzinfo=timezone(timedelta(hours=3))
)


@dataclass(slots=True, kw_only=True)
class LimitsConfig:
    announcement_timeout: int = 10
    # Seconds of setup time assumed between consecutive events when projecting
    # expected start times (see ADR-0008). Matches `duration`, which is seconds.
    transition_buffer: int = 60


@dataclass(slots=True, kw_only=True)
class AppSettings(AggregateRoot):
    # Voting is open when ``now`` falls within [voting_start, voting_end).
    # Both None means voting is closed (the default).
    voting_start: datetime | None = None
    voting_end: datetime | None = None

    festival_start: datetime = DEFAULT_FESTIVAL_START
    # Organizers flip this when the festival is over — the "after" phase is a
    # deliberate switch, not a guessed end date, so the app shows the wrap-up
    # state exactly when they decide (a festival can run long).
    festival_ended: bool = False

    limits: LimitsConfig = field(default_factory=LimitsConfig)

    def set_voting_time_range(
        self,
        *,
        start: datetime | None,
        end: datetime | None,
    ) -> None:
        if start is not None and end is not None and end <= start:
            raise InvalidVotingTimeRange
        self.voting_start = start
        self.voting_end = end

    def is_voting_open(self, *, now: datetime) -> bool:
        if self.voting_start is None or self.voting_end is None:
            return False
        return self.voting_start <= now < self.voting_end

    def set_festival_start(self, *, start: datetime) -> None:
        self.festival_start = start

    def set_festival_ended(self, *, ended: bool) -> None:
        self.festival_ended = ended

    def update_limits(
        self,
        *,
        announcement_timeout: int | None = None,
        transition_buffer: int | None = None,
    ) -> None:
        # Mutation of the nested limits config goes through the aggregate root
        # so callers never reach into it directly. None means "leave as is".
        if announcement_timeout is not None:
            self.limits.announcement_timeout = announcement_timeout
        if transition_buffer is not None:
            self.limits.transition_buffer = transition_buffer
