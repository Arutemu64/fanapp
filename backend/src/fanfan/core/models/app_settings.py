from dataclasses import dataclass, field

from fanfan.core.models.base import AggregateRoot


@dataclass(slots=True, kw_only=True)
class LimitsConfig:
    announcement_timeout_seconds: int = 10
    # Setup time assumed between consecutive events when projecting expected
    # start times (see ADR-0008) — one global value rather than a per-event
    # column, because nobody tunes per-act buffers day-of.
    transition_buffer_seconds: int = 60


@dataclass(slots=True, kw_only=True)
class AppSettings(AggregateRoot):
    voting_enabled: bool = False

    limits: LimitsConfig = field(default_factory=LimitsConfig)

    def set_voting_enabled(self, *, enabled: bool) -> None:
        self.voting_enabled = enabled

    def update_limits(
        self,
        *,
        announcement_timeout_seconds: int | None = None,
        transition_buffer_seconds: int | None = None,
    ) -> None:
        # Mutation of the nested limits config goes through the aggregate root
        # so callers never reach into it directly. None means "leave as is".
        if announcement_timeout_seconds is not None:
            self.limits.announcement_timeout_seconds = announcement_timeout_seconds
        if transition_buffer_seconds is not None:
            self.limits.transition_buffer_seconds = transition_buffer_seconds
