import os
from pathlib import Path

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.db.config import DatabaseConfig

# Go up 5 levels: backend/src/fanfan/adapters/config/parsers.py -> backend/src/fanfan/adapters/config/ -> backend/src/fanfan/adapters/ -> backend/src/fanfan/ -> backend/src/ -> backend/ -> fanapp/
PROJECT_ROOT = Path(__file__).resolve().parents[5]


def get_config() -> EnvConfig:
    env_file = os.getenv("ENV_FILE")
    if not env_file:
        default_env = PROJECT_ROOT / ".env"
        if default_env.exists():
            env_file = default_env

    return EnvConfig(_env_file=env_file)


def get_database_config() -> DatabaseConfig:
    return get_config().db
