import logging
import os
from collections.abc import Iterable

from dishka import Provider, Scope, provide
from pydantic import PostgresDsn
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.valkey import ValkeyContainer

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.redis.config import RedisConfig

logger = logging.getLogger(__name__)


class TestDbProvider(Provider):
    scope = Scope.APP

    @provide
    def get_db_config(self) -> Iterable[DatabaseConfig]:
        # Pinned to match prod/dev (docker-compose.yml) and the cloud prepull
        # (.claude/setup.sh) exactly, alpine variant included: Alpine's musl
        # libc has different collation/locale behavior than the glibc-based
        # image, so testing against the same variant as production avoids
        # sorting bugs that wouldn't show up against a different libc.
        postgres = PostgresContainer("postgres:18.4-alpine", driver="asyncpg")
        # TODO: workaround from testcontainers/testcontainers-python#108.
        # Use 127.0.0.1, not "localhost": redis.asyncio resolves "localhost"
        # to ::1 (IPv6) on Windows, but Docker only binds mapped ports on IPv4.
        if os.name == "nt":
            postgres.get_container_host_ip = lambda: "127.0.0.1"
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
        valkey = ValkeyContainer("valkey/valkey:9.1-alpine")
        # TODO: workaround from testcontainers/testcontainers-python#108.
        if os.name == "nt":
            valkey.get_container_host_ip = lambda: "127.0.0.1"
        try:
            valkey.start()
            host = valkey.get_container_host_ip()
            port = valkey.get_exposed_port()
            redis_config = RedisConfig(
                host=host,
                port=int(port),
            )
            yield redis_config
        finally:
            valkey.stop()
