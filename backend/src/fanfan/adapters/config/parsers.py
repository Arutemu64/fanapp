import os

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.db.config import DatabaseConfig


def get_config() -> EnvConfig:
    return EnvConfig(_env_file=os.getenv("ENV_FILE"))


def get_database_config() -> DatabaseConfig:
    return get_config().db
