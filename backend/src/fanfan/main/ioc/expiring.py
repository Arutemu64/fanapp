from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fanfan.adapters.db.expiring.cooldown import PostgresCooldown
from fanfan.adapters.db.expiring.purger import PostgresExpiredStatePurger
from fanfan.adapters.db.expiring.rate_limiter import PostgresRateLimiter
from fanfan.adapters.db.expiring.session_store import PostgresSessionStore
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

    @provide
    def get_session_store(
        self, sessions: async_sessionmaker[AsyncSession], config: WebConfig
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
