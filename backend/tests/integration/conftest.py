from collections.abc import AsyncIterable
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.command import upgrade
from alembic.config import Config as AlembicConfig
from dishka import AnyOf, AsyncContainer, Provider, Scope, make_async_container
from redis.asyncio import Redis

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.application.ports.email_sender import EmailSender
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.notifier import PushNotifierPort, TelegramNotifierPort
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.main.ioc.db import DbProvider, SqlGatewaysProvider
from fanfan.main.ioc.interactors import InteractorsProvider
from fanfan.main.ioc.jinja import JinjaProvider
from fanfan.main.ioc.redis import RedisProvider
from fanfan.main.ioc.security import SecurityProvider
from fanfan.main.ioc.services import ServicesProvider
from tests.fakes.email_sender import FakeEmailSender
from tests.fakes.event_broker import FakeEventBroker
from tests.fakes.id_provider import FakeIdProvider
from tests.fakes.notifier import FakePushNotifier, FakeTelegramNotifier
from tests.fakes.realtime_gateway import FakeRealtimeGateway
from tests.fixtures.db_provider import TestDbProvider
from tests.fixtures.db_session import TestSessionProvider

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest_asyncio.fixture(scope="session")
async def dishka() -> AsyncIterable[AsyncContainer]:
    # Fakes for ports that would otherwise reach external systems
    # (NATS, SMTP, Telegram, WebPush). REQUEST scope so each test gets a
    # fresh instance and the interactor under test shares it with the test.
    mock_provider = Provider(scope=Scope.REQUEST)
    mock_provider.provide(FakeEventBroker, provides=AnyOf[EventBroker, FakeEventBroker])
    mock_provider.provide(FakeIdProvider, provides=AnyOf[IdProvider, FakeIdProvider])
    mock_provider.provide(FakeEmailSender, provides=AnyOf[EmailSender, FakeEmailSender])
    mock_provider.provide(
        FakeTelegramNotifier,
        provides=AnyOf[TelegramNotifierPort, FakeTelegramNotifier],
    )
    mock_provider.provide(
        FakePushNotifier, provides=AnyOf[PushNotifierPort, FakePushNotifier]
    )
    mock_provider.provide(
        FakeRealtimeGateway, provides=AnyOf[RealtimeGateway, FakeRealtimeGateway]
    )
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
        SecurityProvider(),
        JinjaProvider(),
        # Override DbProvider's session with the rollback-per-test session.
        # Must come after DbProvider so it wins the AsyncSession key.
        TestSessionProvider(),
        # External integrations (NATS broker, Telegram bot, SMTP, OAuth,
        # TicketsCloud/Cosplay2 HTTP clients) are intentionally NOT wired.
        # Interactors that need them are not yet testable here; everything
        # else resolves, so we skip eager dependency validation.
        skip_validation=True,
    )
    yield container
    await container.close()


@pytest_asyncio.fixture
async def dishka_request(dishka: AsyncContainer) -> AsyncIterable[AsyncContainer]:
    async with dishka() as request_container:
        yield request_container


@pytest_asyncio.fixture(autouse=True)
async def reset_redis(dishka_request: AsyncContainer):
    # Redis is not transactional, so (unlike the database, which rolls back
    # via TestSessionProvider) it has to be wiped between tests by hand.
    redis = await dishka_request.get(Redis)
    await redis.flushdb()
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
