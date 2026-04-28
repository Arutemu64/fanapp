from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.redis.config import RedisConfig


class DbConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def get_db_config(self, config: EnvConfig) -> DatabaseConfig:
        return config.db

    @provide
    def get_redis_config(self, config: EnvConfig) -> RedisConfig:
        return config.redis
