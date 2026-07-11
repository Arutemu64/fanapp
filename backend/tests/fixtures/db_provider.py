import logging
import os
from collections.abc import Iterable

from dishka import Provider, Scope, provide
from pydantic import PostgresDsn
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.redis.config import RedisConfig

logger = logging.getLogger(__name__)


class TestDbProvider(Provider):
    scope = Scope.APP

    @provide
    def get_db_config(self) -> Iterable[DatabaseConfig]:
        postgres = PostgresContainer("postgres:18.4", driver="asyncpg")
        # TODO: workaround from testcontainers/testcontainers-python#108.
        if os.name == "nt":
            postgres.get_container_host_ip = lambda: "localhost"
        try:
            postgres.start()
            postgres_url = postgres.get_connection_url()
            logger.info("postgres url %s", postgres_url)
            db_config = DatabaseConfig(url=PostgresDsn(postgres_url), echo=False)
            yield db_config
        finally:
            postgres.stop()

    @provide
    def get_redis_config(self) -> Iterable[RedisConfig]:
        # Match the prod/dev image (docker-compose.yml). RedisContainer pings
        # over the RESP wire with a redis-py client, so Valkey works unchanged.
        # TODO(testcontainers>=4.15.0): switch to the dedicated ValkeyContainer
        # (testcontainers/testcontainers-python#947) once it ships in a stable
        # release; it also drops the deprecated wait-decorator filterwarning.
        redis_container = RedisContainer("valkey/valkey:9.1-alpine")
        # TODO: workaround from testcontainers/testcontainers-python#108.
        if os.name == "nt":
            redis_container.get_container_host_ip = lambda: "localhost"
        try:
            redis_container.start()
            host = redis_container.get_container_host_ip()
            port = redis_container.get_exposed_port(redis_container.port)
            redis_config = RedisConfig(
                host=host,
                port=int(port),
            )
            yield redis_config
        finally:
            redis_container.stop()
