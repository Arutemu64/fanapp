from collections.abc import AsyncIterable
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.command import upgrade
from alembic.config import Config as AlembicConfig
from dishka import AnyOf, AsyncContainer, Provider, Scope, make_async_container
from redis.asyncio import Redis
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.models import (
    MailingORM,
    ScheduleChangeORM,
    ScheduleEventORM,
    UserORM,
    UserPermissionORM,
)
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.id_provider import IdProvider
from fanfan.main.ioc.db import DbProvider, SqlGatewaysProvider
from fanfan.main.ioc.interactors import InteractorsProvider
from fanfan.main.ioc.redis import RedisProvider
from fanfan.main.ioc.services import ServicesProvider
from tests.fixtures.db_provider import TestDbProvider
from tests.fakes.event_broker import FakeEventBroker
from tests.fakes.id_provider import FakeIdProvider

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest_asyncio.fixture(scope="session")
async def dishka() -> AsyncIterable[AsyncContainer]:
    mock_provider = Provider(scope=Scope.APP)
    mock_provider.provide(
        FakeEventBroker,
        provides=AnyOf[EventBroker, FakeEventBroker],
        scope=Scope.REQUEST,
    )
    mock_provider.provide(FakeIdProvider, provides=AnyOf[IdProvider, FakeIdProvider])
    container = make_async_container(
        # Test providers
        mock_provider,
        TestDbProvider(),
        # Real providers
        InteractorsProvider(),
        DbProvider(),
        RedisProvider(),
        ServicesProvider(),
        SqlGatewaysProvider(),
        # Don't validate all dependencies
        skip_validation=True,
    )
    yield container
    await container.close()


@pytest_asyncio.fixture
async def dishka_request(dishka: AsyncContainer) -> AsyncIterable[AsyncContainer]:
    async with dishka() as request_container:
        yield request_container


@pytest_asyncio.fixture(autouse=True)
async def clean_test_data(dishka_request: AsyncContainer):
    session = await dishka_request.get(AsyncSession)
    redis = await dishka_request.get(Redis)

    await session.execute(delete(ScheduleChangeORM))
    await session.execute(delete(MailingORM))
    await session.execute(delete(UserPermissionORM))
    await session.execute(delete(ScheduleEventORM))
    await session.execute(delete(UserORM).where(UserORM.username != "system"))
    await session.commit()
    await redis.delete("rate_limit:announce:timestamp", "rate_limit:announce:lock")
    yield


@pytest_asyncio.fixture(scope="session")
async def alembic_config(dishka: AsyncContainer) -> AlembicConfig:
    alembic_cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location",
        str(BACKEND_DIR / "src" / "fanfan" / "adapters" / "db" / "migrations"),
    )
    db_config = await dishka.get(DatabaseConfig)
    alembic_cfg.set_main_option("sqlalchemy.url", db_config.build_connection_str())
    return alembic_cfg


@pytest.fixture(scope="session", autouse=True)
def upgrade_schema_db(alembic_config: AlembicConfig):
    upgrade(alembic_config, "head")
