from collections.abc import AsyncIterable, AsyncIterator
from contextlib import asynccontextmanager
from typing import override

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from fanfan.adapters.db.expiring.transactions import TransactionSource


class SavepointTransactions(TransactionSource):
    """Runs each expiring-state call in a SAVEPOINT on the test's connection.

    The writes then see rows the test added (the ``auth_sessions`` foreign key
    needs its user) and roll back with everything else at teardown.
    """

    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    @override
    @asynccontextmanager
    async def begin(self) -> AsyncIterator[AsyncConnection]:
        async with self.connection.begin_nested():
            yield self.connection


class TestSessionProvider(Provider):
    """Per-test connection whose outer transaction is always rolled back.

    Each test opens its own connection and starts an outer transaction. The
    session binds to it with ``join_transaction_mode="create_savepoint"``: when
    an interactor calls ``session.commit()`` it only releases a SAVEPOINT, so the
    outer transaction stays open and is rolled back when the test finishes. The
    expiring-state adapters share the connection through
    ``SavepointTransactions``.

    This gives complete isolation for free: no test can see another test's
    writes and nothing is persisted, even though interactors commit normally.
    It replaces manual table cleanup and removes the need to hand-pick unique
    ids across tests.

    Registered AFTER ``DbProvider`` and ``ExpiringStateProvider`` so it
    overrides their session and transaction source (Dishka resolves the last
    provider registered for a given type).
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
    async def get_session(
        self, connection: AsyncConnection
    ) -> AsyncIterable[AsyncSession]:
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()

    @provide
    def get_transactions(self, connection: AsyncConnection) -> TransactionSource:
        return SavepointTransactions(connection)
