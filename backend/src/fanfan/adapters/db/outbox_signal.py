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

# The channel the outbox INSERT trigger raises NOTIFY on. This is a contract
# with the trigger created in the migration
# ``2026_08_26_..._add_outbox_insert_notify_trigger`` — the two literals must
# match, so changing one is a migration, not a rename.
OUTBOX_CHANNEL = "outbox_new"

# Reconnect delay after the LISTEN connection drops: exponential with jitter, so
# a Postgres outage is retried at a falling rate instead of logging a warning
# every second. The poll backstop keeps delivering during the gap, so the cap
# only bounds how long we run in poll-only (slower) mode, not correctness.
_RECONNECT_BASE_DELAY_SECONDS = 1.0
_RECONNECT_MAX_DELAY_SECONDS = 30.0
_RECONNECT_MAX_EXPONENT = 16
# A connection that stayed up this long counts as recovered: its eventual drop
# starts a fresh backoff instead of inheriting the earlier failure count.
_RECONNECT_RESET_AFTER_SECONDS = 60.0

# A LISTEN socket can die silently (NAT idle timeout, firewall drop) without
# the socket ever reporting an error, which would leave the relay on the poll
# backstop until the next restart. A periodic probe turns that into an error the
# supervisor reconnects on. The probe timeout is load-bearing: an unbounded
# query on a half-dead socket waits out the kernel TCP keepalive (~2 h on Linux)
# before failing. Pattern from faststream-outbox:
# https://github.com/modern-python/faststream-outbox/blob/main/faststream_outbox/subscriber/usecase.py
# A timed-out probe is not instant: psycopg first spends up to ~10 s asking the
# server to cancel it, then closes the connection.
_HEALTH_CHECK_INTERVAL_SECONDS = 30.0
_HEALTH_CHECK_TIMEOUT_SECONDS = 5.0


def _reconnect_delay(failures: int) -> float:
    # Clamp the exponent: the cap is hit after a handful of failures, and an
    # unclamped power overflows float once a long outage piles up ~1000 of them.
    exponent = min(failures - 1, _RECONNECT_MAX_EXPONENT)
    multiplier: int = 2**exponent
    delay = _RECONNECT_BASE_DELAY_SECONDS * multiplier
    jitter = random.uniform(0.5, 1.5)  # noqa: S311 - not security-sensitive
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
        # Set by the NOTIFY callback (and on each reconnect); the relay clears it
        # with arm() before draining. Edge-triggered latch, so a signal that
        # lands mid-drain still wakes the following wait.
        self._event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._closing = False

    def arm(self) -> None:
        self._event.clear()

    # ASYNC109 is suppressed below: the timeout is intrinsic to this primitive
    # — wait for a signal, but no longer than the backstop interval — so the
    # wait owns it rather than each caller wrapping the call in a timeout block.
    async def wait(self, timeout: float) -> None:  # noqa: ASYNC109
        # A timeout is the backstop tick: no NOTIFY arrived within the interval,
        # but the relay drains anyway, so a missed notification only ever costs
        # this much latency.
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
            # Await it out so the supervisor's finally block closes the
            # connection before stop() returns.
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
                # A fresh connection may have missed inserts committed while it
                # was down; wake the relay so it drains now instead of waiting
                # out the poll interval.
                self._event.set()
                # Block until the connection drops (or we are cancelled on stop),
                # setting the Event for each notification in the meantime.
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
                    # The socket may already be gone; a close failure is nothing
                    # the supervisor can act on, so swallow it. psycopg's close()
                    # never waits on the server, so a half-dead socket cannot
                    # hang it.
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
                # A bare notification is the whole signal; its channel and
                # payload carry nothing the relay needs.
                async for _notify in connection.notifies(
                    timeout=_HEALTH_CHECK_INTERVAL_SECONDS
                ):
                    self._event.set()
            except psycopg.OperationalError:
                # A server-side drop surfaces here as an error on the socket;
                # anything else is a real failure for the supervisor to log.
                if connection.broken:
                    return
                raise
            # The interval passed: prove the socket still answers.
            await asyncio.wait_for(
                connection.execute("SELECT 1"), _HEALTH_CHECK_TIMEOUT_SECONDS
            )

    async def _connect(self) -> psycopg.AsyncConnection:
        url = make_url(self._config.build_connection_str())
        application_name: str | None = None
        if self._config.application_name is not None:
            # Label this connection in pg_stat_activity distinctly from the
            # pooled query connections, so an idle LISTEN is easy to spot.
            application_name = f"{self._config.application_name}-outbox-listener"
        # Autocommit: LISTEN takes effect only once its transaction commits, and
        # Postgres delivers notifications only between transactions.
        return await psycopg.AsyncConnection.connect(
            host=url.host,
            port=url.port,
            user=url.username,
            password=url.password,
            dbname=url.database,
            # psycopg drops None parameters, leaving the label unset.
            application_name=application_name,
            autocommit=True,
        )
