import os

from dotenv import find_dotenv

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.db.config import DatabaseConfig


def get_config() -> EnvConfig:
    env_file = os.getenv("ENV_FILE") or find_dotenv()
    return EnvConfig(_env_file=env_file)  # ty:ignore[missing-argument, unknown-argument]


def get_database_config() -> DatabaseConfig:
    return get_config().db
