from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator
from uuid import uuid7

import pytest
import pytest_asyncio
from alembic.command import upgrade
from alembic.config import Config as AlembicConfig
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from httpx2 import ASGITransport, AsyncClient
from pydantic import PostgresDsn
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.application.ports.session_store import SessionStore
from fanfan.core.models.user import User
from fanfan.main.ioc.id_provider import WebAuthProvider
from fanfan.presentation.web.config import WebConfig
from fanfan.presentation.web.factory import build_app
from fanfan.presentation.web.routes.auth.cookies import SESSION_COOKIE_NAME
from tests.integration.conftest import make_test_providers

# Postgres clones a database only while nobody is connected to it, so the
# template is migrated once and never opened again.
TEMPLATE_DB = "http_template"


class CloneDbProvider(Provider):
    scope = Scope.APP

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url

    @provide
    def get_db_config(self) -> DatabaseConfig:
        return DatabaseConfig(url=PostgresDsn(self.url), echo=False)


def _with_database(url: str, database: str) -> str:
    return make_url(url).set(database=database).render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def http_template_url(alembic_config: AlembicConfig) -> Iterator[str]:
    server_url = alembic_config.get_main_option("sqlalchemy.url")
    assert server_url is not None
    admin = create_engine(server_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    with admin.connect() as connection:
        connection.execute(text(f"CREATE DATABASE {TEMPLATE_DB}"))

    template_url = _with_database(server_url, TEMPLATE_DB)
    template_config = AlembicConfig(alembic_config.config_file_name)
    template_config.set_main_option(
        "script_location", alembic_config.get_main_option("script_location") or ""
    )
    template_config.set_main_option("sqlalchemy.url", template_url)
    upgrade(template_config, "head")

    yield template_url
    with admin.connect() as connection:
        connection.execute(text(f"DROP DATABASE {TEMPLATE_DB} WITH (FORCE)"))
    admin.dispose()


@pytest_asyncio.fixture(scope="session")
async def admin_engine(http_template_url: str) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(
        http_template_url, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def http_container(
    admin_engine: AsyncEngine, http_template_url: str
) -> AsyncGenerator[AsyncContainer]:
    """The production DI graph on a fresh clone of the migrated database.

    Requests commit for real and the expiring-state adapters keep their own
    pool, as in production; the savepoint harness can't model that, because
    a write off the unit of work would roll back with its savepoint.
    """
    database = f"http_{uuid7().hex}"
    async with admin_engine.connect() as connection:
        await connection.execute(
            text(f"CREATE DATABASE {database} TEMPLATE {TEMPLATE_DB}")
        )

    container = make_async_container(
        *make_test_providers(),
        CloneDbProvider(_with_database(http_template_url, database)),
        FastapiProvider(),
        WebAuthProvider(),
        skip_validation=True,
    )
    try:
        yield container
    finally:
        await container.close()
        async with admin_engine.connect() as connection:
            await connection.execute(text(f"DROP DATABASE {database} WITH (FORCE)"))


@pytest_asyncio.fixture
async def dishka_request(
    http_container: AsyncContainer,
) -> AsyncGenerator[AsyncContainer]:
    """Persona fixtures write through the HTTP container, so requests see them."""
    async with http_container() as request_container:
        yield request_container


@pytest_asyncio.fixture
async def client(http_container: AsyncContainer) -> AsyncGenerator[AsyncClient]:
    web_config = await http_container.get(WebConfig)
    app = build_app(http_container, web_config)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http_client:
        yield http_client


@pytest_asyncio.fixture
async def sign_in(
    dishka_request: AsyncContainer, client: AsyncClient
) -> Callable[[User], Awaitable[None]]:
    """Give the client a session cookie for `user`, skipping the login form.

    `test_auth_session.py` covers the real login; other flows only need to be
    signed in.
    """
    session_store = await dishka_request.get(SessionStore)

    async def _sign_in(user: User) -> None:
        session_id = await session_store.create_session(user.id)
        client.cookies.set(SESSION_COOKIE_NAME, session_id)

    return _sign_in
