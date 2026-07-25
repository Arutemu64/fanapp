import logging
from enum import StrEnum

from pydantic import Field, field_validator, model_validator
from pydantic_extra_types.timezone_name import TimeZoneName
from pydantic_settings import BaseSettings, SettingsConfigDict

from fanfan.adapters.api.cosplay2.config import Cosplay2Config
from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.captcha.config import SmartCaptchaConfig
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
        # "ignore", not "forbid": the backend reads the same root `.env` that also
        # holds Compose/frontend vars (IMAGE_TAG, FRONTEND_PORT, PUBLIC_*, ...),
        # which are not backend fields — "forbid" would crash the app on them.
        # "ignore" drops those silently; a renamed/typo'd BACKEND key is caught by
        # the .env.example drift check instead (see AGENTS.md config-drift rule).
        extra="ignore",
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
    # Read from APP_ENV, not bare ENV: pydantic-settings also reads os.environ,
    # and `ENV` is a common ambient shell var that could silently shadow the
    # .env value. The Python attribute stays `env`.
    env: Environment = Field(validation_alias="APP_ENV")
    # Commit SHA of the running build, baked into the image by the publish
    # workflow (Dockerfile ARG/ENV APP_BUILD) — it identifies *which* build is
    # running, where `version` in pyproject identifies the release. Unset when
    # building from source locally, which is why it is optional. Empty string
    # normalises to None below so an accidental `APP_BUILD=` in .env does not
    # report a blank Sentry release.
    build: str | None = Field(default=None, validation_alias="APP_BUILD")
    # Defaults to production-safe values; relaxed for APP_ENV=dev (see validator).
    debug: DebugConfig = DebugConfig()

    # External
    cosplay2: Cosplay2Config | None = None
    tcloud: TCloudConfig | None = None

    # Captcha (optional — when unset, captcha verification is disabled)
    smartcaptcha: SmartCaptchaConfig | None = None

    # Scheduler
    scheduler: SchedulerConfig = SchedulerConfig()

    # Outbox relay (poll interval, batch size, retention)
    outbox: OutboxConfig = OutboxConfig()

    # Notification retention (age before old notifications are purged)
    notification: NotificationConfig = NotificationConfig()

    @field_validator("build", mode="after")
    @classmethod
    def _blank_build_is_unset(cls, value: str | None) -> str | None:
        return value or None

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
                "DEBUG__ENABLED must be False when APP_ENV=prod "
                "(FastAPI debug mode leaks stack traces in HTTP responses)."
            )
            raise ValueError(msg)
        return self
