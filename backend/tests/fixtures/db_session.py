from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


class TestSessionProvider(Provider):
    """Per-test transactional session that is always rolled back.

    Each test opens its own connection, starts an outer transaction and binds
    a session to it with ``join_transaction_mode="create_savepoint"``. When an
    interactor calls ``session.commit()`` it only releases a SAVEPOINT, so the
    outer transaction stays open and is rolled back when the test finishes.

    This gives complete isolation for free: no test can see another test's
    writes and nothing is persisted, even though interactors commit normally.
    It replaces manual table cleanup and removes the need to hand-pick unique
    ids across tests.

    Registered AFTER ``DbProvider`` so it overrides the production session
    (Dishka resolves the last provider registered for a given type).
    """

    scope = Scope.REQUEST

    @provide
    async def get_session(self, engine: AsyncEngine) -> AsyncIterable[AsyncSession]:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            try:
                yield session
            finally:
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
