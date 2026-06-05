from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.db.config import DatabaseConfig


def get_config() -> EnvConfig:
    return EnvConfig()  # ty:ignore[missing-argument]


def get_database_config() -> DatabaseConfig:
    return get_config().db
