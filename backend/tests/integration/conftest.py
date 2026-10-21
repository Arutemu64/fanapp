from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid7

import pytest
import pytest_asyncio
from alembic.command import upgrade
from alembic.config import Config as AlembicConfig
from dishka import AnyOf, AsyncContainer, Provider, Scope, make_async_container
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.application.ports.email_sender import EmailSender
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.id_provider import IdProvider
from fanfan.application.ports.notifier import (
    PushNotifierPort,
    TelegramNotifierPort,
    VkNotifierPort,
)
from fanfan.application.ports.realtime_gateway import RealtimeGateway
from fanfan.application.ports.sources.cosplay import CosplaySource
from fanfan.application.ports.sources.tickets import TicketsSource
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.base import Message
from fanfan.core.models.permission import UserPermission
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission, generate_user_permission_id
from fanfan.core.vo.user import UserId, Username, UserRole
from fanfan.main.ioc.db import DbProvider, SqlGatewaysProvider
from fanfan.main.ioc.html import HtmlProvider
from fanfan.main.ioc.interactors import InteractorsProvider
from fanfan.main.ioc.jinja import JinjaProvider
from fanfan.main.ioc.profanity import ProfanityProvider
from fanfan.main.ioc.queue import QueueProvider
from fanfan.main.ioc.redis import RedisProvider
from fanfan.main.ioc.security import SecurityProvider
from fanfan.main.ioc.serialization import SerializationProvider
from fanfan.main.ioc.services import ServicesProvider
from fanfan.main.ioc.sync import SyncProvider
from fanfan.presentation.worker.app import routes
from tests.fakes.captcha import FakeCaptchaVerifier
from tests.fakes.cosplay_source import FakeCosplaySource
from tests.fakes.email_sender import FakeEmailSender
from tests.fakes.id_provider import FakeIdProvider
from tests.fakes.notifier import (
    FakePushNotifier,
    FakeTelegramNotifier,
    FakeVkNotifier,
)
from tests.fakes.realtime_gateway import FakeRealtimeGateway
from tests.fakes.tickets_source import FakeTicketsSource
from tests.fixtures.config import TestConfigProvider, TestSyncProvider
from tests.fixtures.db_provider import TestDbProvider
from tests.fixtures.db_session import TestSessionProvider

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest_asyncio.fixture(scope="session")
async def dishka() -> AsyncGenerator[AsyncContainer]:
    # Fakes for ports that would otherwise reach external systems
    # (Redis pub/sub, SMTP, Telegram, WebPush, TicketsCloud). REQUEST scope so
    # each test gets a fresh instance and the interactor under test shares it
    # with the test.
    fakes_provider = Provider(scope=Scope.REQUEST)
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
        FakeVkNotifier, provides=AnyOf[VkNotifierPort, FakeVkNotifier]
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
    fakes_provider.provide(
        FakeCaptchaVerifier, provides=AnyOf[CaptchaVerifier, FakeCaptchaVerifier]
    )
    container = make_async_container(
        # Test providers
        TestDbProvider(),
        TestConfigProvider(),
        # Real providers
        InteractorsProvider(),
        DbProvider(),
        RedisProvider(),
        ServicesProvider(),
        SqlGatewaysProvider(),
        SyncProvider(),
        # Real job queue: messages are written to procrastinate_jobs in the
        # test's own transaction, so a test reads what it queued (`jobs`).
        QueueProvider(),
        SecurityProvider(),
        SerializationProvider(),
        JinjaProvider(),
        # Real word-list filter — pure and offline, so no fake is needed.
        ProfanityProvider(),
        # Real HTML sanitizer (nh3) — pure and offline, same reasoning.
        HtmlProvider(),
        # Override DbProvider's session with the rollback-per-test session.
        # Must come after DbProvider so it wins the AsyncSession key.
        TestSessionProvider(),
        # Same trick: must come after SyncProvider to win AvailableSyncSources,
        # whose real factory reads the EnvConfig tests never build.
        TestSyncProvider(),
        # Last, so each fake wins over a real provider of the same port
        # (RedisProvider's RealtimeGateway).
        fakes_provider,
        # External integrations (Telegram bot, SMTP, OAuth,
        # Cosplay2 HTTP client) are intentionally NOT wired. Interactors that
        # need them are not yet testable here; everything else resolves, so we
        # skip eager dependency validation. (TicketsCloud now has a port + fake,
        # so ticket-sync interactors are testable — see FakeTicketsSource.)
        skip_validation=True,
    )
    yield container
    await container.close()


@pytest_asyncio.fixture
async def dishka_request(dishka: AsyncContainer) -> AsyncGenerator[AsyncContainer]:
    async with dishka() as request_container:
        yield request_container


# --- Shared plumbing fixtures ---------------------------------------------
# Almost every integration test resolves the same request-scoped plumbing:
# the job queue it asserts enqueued messages on, the UnitOfWork it commits
# setup with, and the acting user. Expose them as fixtures so each test body only
# spells out the interactor under test and the repositories/queries it checks.
# The feature-specific dependencies stay explicit via `dishka_request.get()`
# so a reader can see at a glance what each test exercises.


@pytest_asyncio.fixture
async def uow(dishka_request: AsyncContainer) -> UnitOfWork:
    return await dishka_request.get(UnitOfWork)


async def make_broadcaster(dishka_request: AsyncContainer, uow: UnitOfWork) -> User:
    """A user granted notifications:send (no persona fixture exists for it)."""
    user_gateway = await dishka_request.get(UserGateway)
    permission_gateway = await dishka_request.get(UserPermissionGateway)
    broadcaster = User(
        id=UserId(uuid7()),
        username=Username("broadcaster"),
        hashed_password=None,
        role=UserRole.ORGANIZER,
    )
    await user_gateway.add(broadcaster)
    await permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.NOTIFICATIONS_SEND,
            user_id=broadcaster.id,
        )
    )
    await uow.commit()
    return broadcaster


type QueuedJobs = list[tuple[str, dict[str, Any]]]


def as_jobs(*messages: Message) -> QueuedJobs:
    """Render typed messages the way the UnitOfWork queues them.

    Recorded events and enqueued commands are not run on commit — the
    UnitOfWork writes one job per subscribed task, and a worker runs them
    later. Tests assert that the right messages were *queued* by comparing
    against this rendering: (task name, message payload) in queue order.
    """
    return [
        (task.name, message.model_dump(mode="json"))
        for message in messages
        for task in routes[message.subject]
    ]


type JobsReader = Callable[[], Awaitable[QueuedJobs]]


class QueuedReader(Protocol):
    async def __call__[M: Message](self, message_type: type[M]) -> list[M]: ...


@pytest_asyncio.fixture
async def jobs(dishka_request: AsyncContainer) -> JobsReader:
    """Return a reader of the jobs queued so far in this test's transaction."""
    # The UnitOfWork writes jobs on this same session's connection, inside the
    # transaction the test rolls back, so they are visible here and gone after.
    session = await dishka_request.get(AsyncSession)

    async def read() -> QueuedJobs:
        rows = await session.execute(
            text("SELECT task_name, args FROM procrastinate_jobs ORDER BY id")
        )
        return [(task_name, args["message"]) for task_name, args in rows]

    return read


@pytest_asyncio.fixture
async def queued(jobs: JobsReader) -> QueuedReader:
    """Return a reader of the messages of one type queued so far, typed.

    A message queues one job per subscribed task; this reads one task's jobs,
    so each queued message appears once.
    """

    async def read[M: Message](message_type: type[M]) -> list[M]:
        task_name = routes[message_type.subject][0].name
        return [
            message_type.model_validate(payload)
            for name, payload in await jobs()
            if name == task_name
        ]

    return read


@pytest_asyncio.fixture
async def login(dishka_request: AsyncContainer) -> Callable[[User], None]:
    """Return a helper that sets the acting user for the request under test."""
    id_provider = await dishka_request.get(FakeIdProvider)

    def _login(user: User) -> None:
        id_provider.set_current_user_id(user.id)

    return _login


@pytest_asyncio.fixture(autouse=True)
async def reset_redis(dishka_request: AsyncContainer) -> AsyncGenerator[None]:
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
def upgrade_schema_db(alembic_config: AlembicConfig) -> None:
    upgrade(alembic_config, "head")
