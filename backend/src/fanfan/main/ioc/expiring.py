from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.expiring.cooldown import PostgresCooldown
from fanfan.adapters.db.expiring.purger import PostgresExpiredStatePurger
from fanfan.adapters.db.expiring.rate_limiter import PostgresRateLimiter
from fanfan.adapters.db.expiring.session_store import PostgresSessionStore
from fanfan.adapters.db.expiring.sessions import (
    ExpiringSessionFactory,
    create_expiring_engine,
)
from fanfan.adapters.db.expiring.token_registry import PostgresTokenRegistry
from fanfan.application.ports.cooldown import Cooldown
from fanfan.application.ports.expired_state import ExpiredStatePurger
from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.application.ports.session_store import SessionStore
from fanfan.application.ports.token_registry import TokenRegistry
from fanfan.presentation.web.config import WebConfig


class ExpiringStateProvider(Provider):
    # Request scope lets tests bind the session factory to their own connection.
    scope = Scope.REQUEST

    @provide(scope=Scope.APP)
    async def get_sessions(
        self, config: DatabaseConfig
    ) -> AsyncIterable[ExpiringSessionFactory]:
        engine = create_expiring_engine(config)
        yield ExpiringSessionFactory(bind=engine, expire_on_commit=False)
        await engine.dispose()

    @provide
    def get_session_store(
        self, sessions: ExpiringSessionFactory, config: WebConfig
    ) -> SessionStore:
        return PostgresSessionStore(
            sessions=sessions,
            ttl_seconds=config.session_ttl_seconds,
            touch_threshold_seconds=config.session_touch_threshold_seconds,
        )

    token_registry = provide(PostgresTokenRegistry, provides=TokenRegistry)
    cooldown = provide(PostgresCooldown, provides=Cooldown)
    rate_limiter = provide(PostgresRateLimiter, provides=RateLimiter)
    purger = provide(PostgresExpiredStatePurger, provides=ExpiredStatePurger)
