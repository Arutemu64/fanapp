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
from fanfan.application.interactors.outbox.config import OutboxConfig
from fanfan.presentation.scheduler.config import SchedulerConfig
from fanfan.presentation.tgbot.config import TelegramConfig
from fanfan.presentation.web.config import WebConfig


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
    env: str
    debug: DebugConfig

    # External
    cosplay2: Cosplay2Config | None = None
    tcloud: TCloudConfig | None = None

    # Captcha (optional — when unset, captcha verification is disabled)
    turnstile: TurnstileConfig | None = None

    # Scheduler
    scheduler: SchedulerConfig = SchedulerConfig()

    # Outbox relay (poll interval, batch size, retention)
    outbox: OutboxConfig = OutboxConfig()
