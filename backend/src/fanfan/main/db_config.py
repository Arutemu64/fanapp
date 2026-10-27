from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.db.config import DatabaseConfig


class DbConfigProvider(Provider):
    scope = Scope.APP

    @provide
    def get_db_config(self, config: EnvConfig) -> DatabaseConfig:
        return config.db
