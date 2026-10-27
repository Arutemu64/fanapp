from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)


class TestSessionProvider(Provider):
    """Per-test connection whose outer transaction is always rolled back.

    Each test opens its own connection and starts an outer transaction. Every
    session binds to it with ``join_transaction_mode="create_savepoint"``, so a
    ``commit()`` only releases a SAVEPOINT and the outer transaction is rolled
    back when the test finishes
    (https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites).
    The unit of work's session and the expiring-state adapters' sessions share
    the connection, so they see each other's rows.

    This gives complete isolation for free: no test can see another test's
    writes and nothing is persisted, even though interactors commit normally.
    It replaces manual table cleanup and removes the need to hand-pick unique
    ids across tests.

    Registered AFTER ``DbProvider`` so it overrides the production session and
    session factory (Dishka resolves the last provider registered for a type).
    """

    scope = Scope.REQUEST

    @provide
    async def get_connection(
        self, engine: AsyncEngine
    ) -> AsyncIterable[AsyncConnection]:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                yield connection
            finally:
                if transaction.is_active:
                    await transaction.rollback()

    @provide
    def get_session_factory(
        self, connection: AsyncConnection
    ) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

    @provide
    async def get_session(
        self, sessions: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with sessions() as session:
            yield session
