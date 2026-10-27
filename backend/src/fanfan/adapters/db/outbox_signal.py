import asyncio
import contextlib
import logging
import random
import time

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.application.ports.outbox_signal import OutboxSignal

logger = logging.getLogger(__name__)

OUTBOX_CHANNEL = "outbox_new"

_RECONNECT_BASE_DELAY_SECONDS = 1.0
_RECONNECT_MAX_DELAY_SECONDS = 30.0
_RECONNECT_MAX_EXPONENT = 16
_RECONNECT_RESET_AFTER_SECONDS = 60.0

_HEALTH_CHECK_INTERVAL_SECONDS = 30.0
_HEALTH_CHECK_TIMEOUT_SECONDS = 5.0


def _reconnect_delay(failures: int) -> float:
    exponent = min(failures - 1, _RECONNECT_MAX_EXPONENT)
    multiplier: int = 2**exponent
    delay = _RECONNECT_BASE_DELAY_SECONDS * multiplier
    jitter = random.uniform(0.5, 1.5)  # noqa: S311
    return min(delay * jitter, _RECONNECT_MAX_DELAY_SECONDS)


class PostgresOutboxSignal(OutboxSignal):
    """LISTEN/NOTIFY wake-up backed by a dedicated psycopg connection.

    Holds one long-lived connection outside the SQLAlchemy pool (a LISTEN
    connection is pinned for the lifetime of the subscription, so it must not
    occupy a pooled slot). A supervisor task keeps it open, probing it for silent
    drops and reconnecting with backoff when it drops; every (re)connect nudges a
    drain so events enqueued while the listener was down are picked up
    immediately rather than waiting for the poll backstop.
    """

    def __init__(self, config: DatabaseConfig, channel: str = OUTBOX_CHANNEL) -> None:
        self._config = config
        self._channel = channel
        self._event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._closing = False

    def arm(self) -> None:
        self._event.clear()

    async def wait(self, timeout: float) -> None:  # noqa: ASYNC109
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._event.wait(), timeout)

    async def start(self) -> None:
        if self._task is not None:
            return
        self._closing = False
        self._task = asyncio.create_task(self._supervise(), name="outbox-listener")

    async def stop(self) -> None:
        self._closing = True
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _supervise(self) -> None:
        failures = 0
        while not self._closing:
            connection: psycopg.AsyncConnection | None = None
            connected_at: float | None = None
            try:
                connection = await self._connect()
                await connection.execute(
                    sql.SQL("LISTEN {}").format(sql.Identifier(self._channel))
                )
                connected_at = time.monotonic()
                self._event.set()
                await self._hold(connection)
                if self._closing:
                    return
                logger.warning(
                    "Outbox LISTEN connection lost; reconnecting",
                    extra={"relay_event": "listener_lost"},
                )
            except Exception:
                logger.warning(
                    "Outbox LISTEN connection failed; reconnecting",
                    exc_info=True,
                    extra={"relay_event": "listener_failed"},
                )
            finally:
                if connection is not None:
                    with contextlib.suppress(Exception):
                        await connection.close()
            if connected_at is not None:
                uptime = time.monotonic() - connected_at
                if uptime >= _RECONNECT_RESET_AFTER_SECONDS:
                    failures = 0
            failures += 1
            await asyncio.sleep(_reconnect_delay(failures))

    async def _hold(self, connection: psycopg.AsyncConnection) -> None:
        """Return once the connection drops; raise if a health probe fails."""
        while True:
            try:
                async for _notify in connection.notifies(
                    timeout=_HEALTH_CHECK_INTERVAL_SECONDS
                ):
                    self._event.set()
            except psycopg.OperationalError:
                if connection.broken:
                    return
                raise
            await asyncio.wait_for(
                connection.execute("SELECT 1"), _HEALTH_CHECK_TIMEOUT_SECONDS
            )

    async def _connect(self) -> psycopg.AsyncConnection:
        url = make_url(self._config.build_connection_str())
        application_name: str | None = None
        if self._config.application_name is not None:
            application_name = f"{self._config.application_name}-outbox-listener"
        return await psycopg.AsyncConnection.connect(
            host=url.host,
            port=url.port,
            user=url.username,
            password=url.password,
            dbname=url.database,
            application_name=application_name,
            autocommit=True,
        )
