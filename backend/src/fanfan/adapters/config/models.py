from pydantic_extra_types.timezone_name import TimeZoneName
from pydantic_settings import BaseSettings, SettingsConfigDict

from fanfan.adapters.api.cosplay2.config import Cosplay2Config
from fanfan.adapters.api.ticketscloud.config import TCloudConfig
from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.debug.config import DebugConfig
from fanfan.adapters.mail.config import MailConfig
from fanfan.adapters.nats.config import NatsConfig
from fanfan.adapters.notifications.config import PushConfig
from fanfan.adapters.redis.config import RedisConfig
from fanfan.presentation.tgbot.config import BotConfig
from fanfan.presentation.web.config import WebConfig


class EnvConfig(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="allow")

    # General
    web: WebConfig
    timezone: TimeZoneName = "Europe/Moscow"

    # Environment
    db: DatabaseConfig
    redis: RedisConfig
    nats: NatsConfig
    mail: MailConfig

    # Notifications
    bot: BotConfig
    push: PushConfig

    # Debug
    env: str
    debug: DebugConfig

    # External
    cosplay2: Cosplay2Config | None = None
    tcloud: TCloudConfig | None = None
