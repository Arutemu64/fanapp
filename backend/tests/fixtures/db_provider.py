import logging
import os
from collections.abc import Iterable

from dishka import Provider, Scope, provide
from pydantic import PostgresDsn
from testcontainers.community.postgres import PostgresContainer

from fanfan.adapters.db.config import DatabaseConfig

logger = logging.getLogger(__name__)


class TestDbProvider(Provider):
    scope = Scope.APP

    @provide
    def get_db_config(self) -> Iterable[DatabaseConfig]:
        postgres = PostgresContainer(
            "postgres:19.0-alpine@sha256:cac45fb483caee3668946088a1c0532db89d5285c28dbfeac889b4068296e06f",
            driver="psycopg",
        )
        if os.name == "nt":
            postgres.get_container_host_ip = lambda: "127.0.0.1"
        try:
            postgres.start()
            postgres_url = postgres.get_connection_url()
            logger.info("postgres url %s", postgres_url)
            yield DatabaseConfig(url=PostgresDsn(postgres_url), echo=False)
        finally:
            postgres.stop()
