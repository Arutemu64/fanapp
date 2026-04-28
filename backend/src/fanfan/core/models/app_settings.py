from dataclasses import dataclass, field


@dataclass(slots=True, kw_only=True)
class LimitsConfig:
    announcement_timeout: int = 10

    def set_announcement_timeout(self, seconds: int) -> None:
        self.announcement_timeout = seconds


@dataclass(slots=True, kw_only=True)
class AppSettings:
    voting_enabled: bool = False

    limits: LimitsConfig = field(default_factory=LimitsConfig)

    def set_voting_enabled(self, enabled: bool) -> None:
        self.voting_enabled = enabled
