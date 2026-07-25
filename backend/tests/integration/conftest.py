from collections.abc import AsyncIterable, Callable
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
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.notifier import PushNotifierPort, TelegramNotifierPort
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.sources.cosplay import CosplaySource
from fanfan.application.ports.sources.tickets import TicketsSource
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.base import AppEvent
from fanfan.core.models.user import User
from fanfan.main.ioc.db import DbProvider, SqlGatewaysProvider
from fanfan.main.ioc.interactors import InteractorsProvider
from fanfan.main.ioc.jinja import JinjaProvider
from fanfan.main.ioc.redis import RedisProvider
from fanfan.main.ioc.security import SecurityProvider
from fanfan.main.ioc.serialization import SerializationProvider
from fanfan.main.ioc.services import ServicesProvider
from fanfan.main.ioc.sync import SyncProvider
from tests.fakes.cosplay_source import FakeCosplaySource
from tests.fakes.email_sender import FakeEmailSender
from tests.fakes.event_broker import FakeEventBroker
from tests.fakes.id_provider import FakeIdProvider
from tests.fakes.notifier import FakePushNotifier, FakeTelegramNotifier
from tests.fakes.realtime_gateway import FakeRealtimeGateway
from tests.fakes.tickets_source import FakeTicketsSource
from tests.fixtures.config import TestConfigProvider, TestSyncProvider
from tests.fixtures.db_provider import TestDbProvider
from tests.fixtures.db_session import TestSessionProvider

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest_asyncio.fixture(scope="session")
async def dishka() -> AsyncIterable[AsyncContainer]:
    # Fakes for ports that would otherwise reach external systems
    # (NATS, SMTP, Telegram, WebPush, TicketsCloud). REQUEST scope so each test
    # gets a fresh instance and the interactor under test shares it with the test.
    fakes_provider = Provider(scope=Scope.REQUEST)
    fakes_provider.provide(
        FakeEventBroker, provides=AnyOf[EventBroker, FakeEventBroker]
    )
    fakes_provider.provide(FakeIdProvider, provides=AnyOf[IdProvider, FakeIdProvider])
    fakes_provider.provide(
        FakeEmailSender, provides=AnyOf[EmailSender, FakeEmailSender]
    )
    fakes_provider.provide(
        FakeTelegramNotifier,
        provides=AnyOf[TelegramNotifierPort, FakeTelegramNotifier],
    )
    fakes_provider.provide(
        FakePushNotifier, provides=AnyOf[PushNotifierPort, FakePushNotifier]
    )
    fakes_provider.provide(
        FakeRealtimeGateway, provides=AnyOf[RealtimeGateway, FakeRealtimeGateway]
    )
    fakes_provider.provide(
        FakeTicketsSource, provides=AnyOf[TicketsSource, FakeTicketsSource]
    )
    fakes_provider.provide(
        FakeCosplaySource, provides=AnyOf[CosplaySource, FakeCosplaySource]
    )
    container = make_async_container(
        # Test providers
        fakes_provider,
        TestDbProvider(),
        TestConfigProvider(),
        # Real providers
        InteractorsProvider(),
        DbProvider(),
        RedisProvider(),
        ServicesProvider(),
        SqlGatewaysProvider(),
        SyncProvider(),
        SecurityProvider(),
        SerializationProvider(),
        JinjaProvider(),
        # Override DbProvider's session with the rollback-per-test session.
        # Must come after DbProvider so it wins the AsyncSession key.
        TestSessionProvider(),
        # Same trick: must come after SyncProvider to win AvailableSyncSources,
        # whose real factory reads the EnvConfig tests never build.
        TestSyncProvider(),
        # External integrations (NATS broker, Telegram bot, SMTP, OAuth,
        # Cosplay2 HTTP client) are intentionally NOT wired. Interactors that
        # need them are not yet testable here; everything else resolves, so we
        # skip eager dependency validation. (TicketsCloud now has a port + fake,
        # so ticket-sync interactors are testable — see FakeTicketsSource.)
        skip_validation=True,
    )
    yield container
    await container.close()


@pytest_asyncio.fixture
async def dishka_request(dishka: AsyncContainer) -> AsyncIterable[AsyncContainer]:
    async with dishka() as request_container:
        yield request_container


# --- Shared plumbing fixtures ---------------------------------------------
# Almost every integration test resolves the same request-scoped plumbing:
# the outbox it asserts enqueued events on, the UnitOfWork it commits setup
# with, and the acting user. Expose them as fixtures so each test body only
# spells out the interactor under test and the repositories/queries it checks.
# The feature-specific dependencies stay explicit via `dishka_request.get()`
# so a reader can see at a glance what each test exercises.


@pytest_asyncio.fixture
async def uow(dishka_request: AsyncContainer) -> UnitOfWork:
    return await dishka_request.get(UnitOfWork)


def as_outbox(*events: AppEvent) -> list[tuple[str, dict]]:
    """Render typed domain events the way they land in the outbox table.

    Aggregate events are no longer published on commit — the UnitOfWork writes
    them to the outbox, and the relay delivers them later. Tests assert that the
    right events were *enqueued* by comparing against this serialization.
    """
    return [(e.subject, e.model_dump(mode="json")) for e in events]


@pytest_asyncio.fixture
async def outbox(dishka_request: AsyncContainer) -> OutboxGateway:
    # Read post-run like events_broker: the UnitOfWork writes events to the same
    # session the test rolls back, so fetch_unpublished returns what was enqueued.
    return await dishka_request.get(OutboxGateway)


@pytest_asyncio.fixture
async def login(dishka_request: AsyncContainer) -> Callable[[User], None]:
    """Return a helper that sets the acting user for the request under test."""
    id_provider = await dishka_request.get(FakeIdProvider)

    def _login(user: User) -> None:
        id_provider.set_current_user_id(user.id)

    return _login


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
