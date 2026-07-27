from dataclasses import dataclass, field

from fanfan.core.models.base import AggregateRoot


@dataclass(slots=True, kw_only=True)
class LimitsConfig:
    announcement_timeout: int = 10
    # Seconds of setup time assumed between consecutive events when projecting
    # expected start times (see ADR-0008). Matches `duration`, which is seconds.
    transition_buffer: int = 60


@dataclass(slots=True, kw_only=True)
class AppSettings(AggregateRoot):
    voting_enabled: bool = False

    limits: LimitsConfig = field(default_factory=LimitsConfig)

    def set_voting_enabled(self, *, enabled: bool) -> None:
        self.voting_enabled = enabled

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
