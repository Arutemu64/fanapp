import logging
from enum import StrEnum

from pydantic import Field, model_validator
from pydantic_extra_types.timezone_name import TimeZoneName
from pydantic_settings import BaseSettings, SettingsConfigDict

from fanfan.adapters.api.cosplay2.config import Cosplay2Config
from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.captcha.config import AltchaConfig
from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.debug.config import DebugConfig
from fanfan.adapters.mail.config import MailConfig
from fanfan.adapters.nats.config import NatsConfig
from fanfan.adapters.push.config import PushConfig
from fanfan.adapters.tgbot.config import TelegramConfig
from fanfan.adapters.vk.config import VkConfig
from fanfan.application.interactors.notifications.config import NotificationConfig
from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.presentation.faststream.schedules.config import SchedulerConfig
from fanfan.presentation.web.config import WebConfig


class Environment(StrEnum):
    """Deployment environment. Single source of truth for dev/prod posture."""

    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    web: WebConfig
    timezone: TimeZoneName = "Europe/Moscow"

    db: DatabaseConfig
    nats: NatsConfig
    mail: MailConfig | None = None

    bot: TelegramConfig
    push: PushConfig

    vk: VkConfig

    env: Environment = Field(validation_alias="APP_ENV")
    debug: DebugConfig = DebugConfig()

    cosplay2: Cosplay2Config | None = None
    tcloud: TCloudConfig | None = None

    altcha: AltchaConfig | None = None

    scheduler: SchedulerConfig = SchedulerConfig()

    outbox: OutboxConfig = OutboxConfig()

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
        elif self.env is Environment.PROD:
            if self.debug.enabled:
                msg = (
                    "DEBUG__ENABLED must be False when APP_ENV=prod "
                    "(FastAPI debug mode leaks stack traces in HTTP responses)."
                )
                raise ValueError(msg)
            if not self.web.cookie_secure:
                msg = (
                    "WEB__COOKIE_SECURE must be True when APP_ENV=prod "
                    "(cookies without Secure are sent over plain HTTP)."
                )
                raise ValueError(msg)
        return self
