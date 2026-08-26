from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from fanfan.core.exceptions.settings import InvalidVotingTimeRange
from fanfan.core.models.base import AggregateRoot

# Programme opening and close, Moscow time (UTC+3). The defaults the app ships
# with until organizers override them from the settings page; together they
# drive the home-page countdown and the before/during/after phase boundaries.
DEFAULT_FESTIVAL_START = datetime(
    2026, 8, 22, 11, 30, tzinfo=timezone(timedelta(hours=3))
)
DEFAULT_FESTIVAL_END = datetime(2026, 8, 23, 20, 0, tzinfo=timezone(timedelta(hours=3)))


@dataclass(slots=True, kw_only=True)
class LimitsConfig:
    announcement_timeout: int = 10


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

    def set_festival_start(self, *, start: datetime) -> None:
        self.festival_start = start

    def set_festival_end(self, *, end: datetime) -> None:
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
