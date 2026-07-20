from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from fanfan.adapters.db.config import DatabaseConfig


def create_engine(config: DatabaseConfig) -> AsyncEngine:
    return create_async_engine(
        url=config.build_connection_str(),
        echo=config.echo,
        pool_pre_ping=True,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_recycle=config.pool_recycle,
        # server_settings is asyncpg-specific; it applies the safety timeouts and
        # application_name label to every connection this engine opens.
        connect_args={"server_settings": config.build_server_settings()},
    )


def create_session_pool(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )
