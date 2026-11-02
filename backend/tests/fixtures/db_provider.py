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
            "postgres:18.6-alpine@sha256:10a5c69a83035ab5239f5620d708520e8b28f5aa1f2b20143e6024532edadfb5",
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
