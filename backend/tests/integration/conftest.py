from collections.abc import AsyncGenerator, Callable
from pathlib import Path
from typing import Any
from uuid import uuid7

import pytest
import pytest_asyncio
from alembic.command import upgrade
from alembic.config import Config as AlembicConfig
from dishka import AnyOf, AsyncContainer, Provider, Scope, make_async_container
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.application.ports.email_sender import EmailSender
from fanfan.application.ports.events_broker import EventBroker
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
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
from fanfan.main.ioc.expiring import ExpiringStateProvider
from fanfan.main.ioc.html import HtmlProvider
from fanfan.main.ioc.interactors import InteractorsProvider
from fanfan.main.ioc.jinja import JinjaProvider
from fanfan.main.ioc.profanity import ProfanityProvider
from fanfan.main.ioc.security import SecurityProvider
from fanfan.main.ioc.serialization import SerializationProvider
from fanfan.main.ioc.services import ServicesProvider
from fanfan.main.ioc.sync import SyncProvider
from tests.fakes.captcha import FakeCaptchaVerifier
from tests.fakes.cosplay_source import FakeCosplaySource
from tests.fakes.email_sender import FakeEmailSender
from tests.fakes.event_broker import FakeEventBroker
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
        fakes_provider,
        TestDbProvider(),
        TestConfigProvider(),
        InteractorsProvider(),
        DbProvider(),
        ExpiringStateProvider(),
        ServicesProvider(),
        SqlGatewaysProvider(),
        SyncProvider(),
        SecurityProvider(),
        SerializationProvider(),
        JinjaProvider(),
        ProfanityProvider(),
        HtmlProvider(),
        TestSessionProvider(),
        TestSyncProvider(),
        skip_validation=True,
    )
    yield container
    await container.close()


@pytest_asyncio.fixture
async def dishka_request(dishka: AsyncContainer) -> AsyncGenerator[AsyncContainer]:
    async with dishka() as request_container:
        yield request_container


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


def as_outbox(*messages: Message) -> list[tuple[str, dict[str, Any]]]:
    """Render typed messages the way they land in the outbox table.

    Recorded events and enqueued commands are not published on commit — the
    UnitOfWork writes them to the outbox, and the relay delivers them later.
    Tests assert that the right messages were *enqueued* by comparing against
    this serialization.
    """
    return [(m.subject, m.model_dump(mode="json")) for m in messages]


@pytest_asyncio.fixture
async def outbox(dishka_request: AsyncContainer) -> OutboxGateway:
    return await dishka_request.get(OutboxGateway)


@pytest_asyncio.fixture
async def login(dishka_request: AsyncContainer) -> Callable[[User], None]:
    """Return a helper that sets the acting user for the request under test."""
    id_provider = await dishka_request.get(FakeIdProvider)

    def _login(user: User) -> None:
        id_provider.set_current_user_id(user.id)

    return _login


@pytest_asyncio.fixture(autouse=True)
async def reset_expiring_state(dishka_request: AsyncContainer) -> None:
    """Expiring-state adapters commit on their own connections, outside the
    rolled-back test transaction, so their tables are emptied between tests.
    """
    engine = await dishka_request.get(AsyncEngine)
    async with engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE auth_sessions, auth_codes, rate_limits, cooldowns")
        )


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
