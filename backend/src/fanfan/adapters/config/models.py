import logging
from enum import StrEnum

from pydantic import model_validator
from pydantic_extra_types.timezone_name import TimeZoneName
from pydantic_settings import BaseSettings, SettingsConfigDict

from fanfan.adapters.api.cosplay2.config import Cosplay2Config
from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.captcha.config import TurnstileConfig
from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.debug.config import DebugConfig
from fanfan.adapters.mail.config import MailConfig
from fanfan.adapters.nats.config import NatsConfig
from fanfan.adapters.push.config import PushConfig
from fanfan.adapters.redis.config import RedisConfig
from fanfan.application.interactors.notifications.config import NotificationConfig
from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.presentation.scheduler.config import SchedulerConfig
from fanfan.presentation.tgbot.config import TelegramConfig
from fanfan.presentation.web.config import WebConfig


class Environment(StrEnum):
    """Deployment environment. Single source of truth for dev/prod posture."""

    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="allow",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # General
    web: WebConfig
    timezone: TimeZoneName = "Europe/Moscow"

    # Environment
    db: DatabaseConfig
    redis: RedisConfig
    nats: NatsConfig
    # Optional — when unset, outgoing emails are logged instead of sent.
    mail: MailConfig | None = None

    # Notifications
    bot: TelegramConfig
    push: PushConfig

    # Debug
    env: Environment
    # Defaults to production-safe values; relaxed for ENV=dev (see validator).
    debug: DebugConfig = DebugConfig()

    # External
    cosplay2: Cosplay2Config | None = None
    tcloud: TCloudConfig | None = None

    # Captcha (optional — when unset, captcha verification is disabled)
    turnstile: TurnstileConfig | None = None

    # Scheduler
    scheduler: SchedulerConfig = SchedulerConfig()

    # Outbox relay (poll interval, batch size, retention)
    outbox: OutboxConfig = OutboxConfig()

    # Notification retention (age before old notifications are purged)
    notification: NotificationConfig = NotificationConfig()

    @model_validator(mode="after")
    def _apply_environment_posture(self) -> EnvConfig:
        """Derive debug defaults from ENV, then fail closed in production.

        DebugConfig ships production-safe defaults. In dev we relax them for a
        better local experience, but only for flags the user did NOT set
        explicitly (an explicit DEBUG__* always wins). staging/prod keep the
        safe defaults untouched.
        """
        explicit = self.debug.model_fields_set
        if self.env is Environment.DEV:
            if "enabled" not in explicit:
                self.debug.enabled = True
            if "logging_level" not in explicit:
                self.debug.logging_level = logging.DEBUG
            if "json_logs" not in explicit:
                self.debug.json_logs = False
        elif self.env is Environment.PROD and self.debug.enabled:
            # FastAPI debug mode leaks stack traces in HTTP responses, so it
            # must never reach production — refuse to start rather than leak.
            msg = (
                "DEBUG__ENABLED must be False when ENV=prod "
                "(FastAPI debug mode leaks stack traces in HTTP responses)."
            )
            raise ValueError(msg)
        return self
