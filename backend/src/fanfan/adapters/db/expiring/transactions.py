from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncConnection


class TransactionSource(Protocol):
    """Opens the short transaction each expiring-state call runs in.

    Production passes the ``AsyncEngine``. Tests pass a savepoint on the test's
    own connection, so these writes see and roll back with the test's rows.
    """

    def begin(self) -> AbstractAsyncContextManager[AsyncConnection]: ...
