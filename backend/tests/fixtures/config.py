from dishka import Provider, Scope, provide
from pydantic import HttpUrl, SecretStr
from pydantic_extra_types.timezone_name import TimeZoneName

from fanfan.application.interactors.sync.get_sync_sources import AvailableSyncSources
from fanfan.core.vo.sync import SyncSource
from fanfan.presentation.web.config import WebConfig


class TestConfigProvider(Provider):
    """Provides the slice of app config the resolvable interactors need.

    The full ``EnvConfig`` is not built in tests (it pulls in NATS, Telegram,
    SMTP, etc., none of which are wired). ``WebConfig`` (session store, token
    registry) and ``timezone`` (Jinja env used to render email codes) are the
    cross-cutting slices the interactors need, so they are supplied here with
    fixed test values, the same way ``TestDbProvider`` supplies the DB and Redis
    configs.
    """

    scope = Scope.APP

    @provide
    def get_web_config(self) -> WebConfig:
        return WebConfig(
            host="localhost",
            port=8000,
            public_url=HttpUrl("http://localhost:3000/"),
            secret_key=SecretStr("test-secret-key"),
        )

    @provide
    def get_timezone(self) -> TimeZoneName:
        return TimeZoneName("Europe/Moscow")


class TestSyncProvider(Provider):
    """Overrides SyncProvider's availability lookup, which reads ``EnvConfig``.

    Registered *after* ``SyncProvider`` so it wins the ``AvailableSyncSources``
    key (Dishka resolves the last provider registered for a type), the same way
    ``TestSessionProvider`` overrides the session from ``DbProvider``. Both
    vendors count as configured: the full ``EnvConfig`` is never built in tests,
    and the sync interactors run against fakes for both sources.
    """

    scope = Scope.APP

    @provide
    def get_available_sync_sources(self) -> AvailableSyncSources:
        return AvailableSyncSources(frozenset(SyncSource))
