import asyncio
import contextlib
import logging

import asyncpg
from sqlalchemy.engine import make_url

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.application.ports.outbox_signal import OutboxSignal

logger = logging.getLogger(__name__)

# The channel the outbox INSERT trigger raises NOTIFY on. This is a contract
# with the trigger created in the migration
# ``2026_08_26_..._add_outbox_insert_notify_trigger`` — the two literals must
# match, so changing one is a migration, not a rename.
OUTBOX_CHANNEL = "outbox_new"

# How long to wait before re-opening the LISTEN connection after it drops. The
# poll backstop keeps delivering during the gap, so this only bounds how long
# we run in poll-only (slower) mode, not correctness.
_RECONNECT_DELAY_SECONDS = 1.0


class PostgresOutboxSignal(OutboxSignal):
    """LISTEN/NOTIFY wake-up backed by a dedicated asyncpg connection.

    Holds one long-lived connection outside the SQLAlchemy pool (a LISTEN
    connection is pinned for the lifetime of the subscription, so it must not
    occupy a pooled slot). A supervisor task keeps it open, reconnecting when it
    drops; every (re)connect nudges a drain so events enqueued while the listener
    was down are picked up immediately rather than waiting for the poll backstop.
    """

    def __init__(self, config: DatabaseConfig, channel: str = OUTBOX_CHANNEL):
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
            # Await the cancelled task so its connection is closed before we
            # return (the supervisor's finally block does the cleanup).
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def _on_notify(
        self, _connection: object, _pid: int, _channel: str, _payload: str
    ) -> None:
        # asyncpg calls this positionally with (connection, pid, channel,
        # payload); we need none of them — a bare notification is the whole
        # signal. It runs on the event loop, so setting the Event is safe.
        self._event.set()

    async def _supervise(self) -> None:
        while not self._closing:
            connection: asyncpg.Connection | None = None
            try:
                connection = await self._connect()
                await connection.add_listener(self._channel, self._on_notify)
                # A fresh connection may have missed inserts committed while it
                # was down; wake the relay so it drains now instead of waiting
                # out the poll interval.
                self._event.set()

                terminated = asyncio.Event()
                # Bind `terminated` as a default arg: the supervisor reassigns it
                # each reconnect, and this callback must fire the current one.
                connection.add_termination_listener(
                    lambda _conn, ev=terminated: ev.set()
                )
                # Block until the connection drops (or we are cancelled on stop).
                # Notifications arrive via the callback in the meantime.
                await terminated.wait()
                if not self._closing:
                    logger.warning("Outbox LISTEN connection lost; reconnecting")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning(
                    "Outbox LISTEN connection failed; retrying", exc_info=True
                )
            finally:
                if connection is not None:
                    # The socket may already be gone; a close failure is nothing
                    # the supervisor can act on, so swallow it.
                    with contextlib.suppress(Exception):
                        await connection.close()
            if not self._closing:
                await asyncio.sleep(_RECONNECT_DELAY_SECONDS)

    async def _connect(self) -> asyncpg.Connection:
        url = make_url(self._config.build_connection_str())
        server_settings: dict[str, str] = {}
        if self._config.application_name is not None:
            # Label this connection in pg_stat_activity distinctly from the
            # pooled query connections, so an idle LISTEN is easy to spot.
            server_settings["application_name"] = (
                f"{self._config.application_name}-outbox-listener"
            )
        return await asyncpg.connect(
            host=url.host,
            port=url.port,
            user=url.username,
            password=url.password,
            database=url.database,
            server_settings=server_settings or None,
        )
