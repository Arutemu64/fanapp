import asyncio
from uuid import uuid7

import asyncpg
import pytest
from dishka import AsyncContainer
from sqlalchemy.engine import make_url

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.outbox_signal import PostgresOutboxSignal

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _raw_connect(config: DatabaseConfig) -> asyncpg.Connection:
    url = make_url(config.build_connection_str())
    return await asyncpg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.database,
    )


async def test_insert_trigger_wakes_the_listener(dishka: AsyncContainer):
    # End-to-end over a real database: the migration's AFTER INSERT trigger must
    # pg_notify on the exact channel the adapter LISTENs on, or notifications
    # would silently fall back to poll-only latency. The per-test session rolls
    # back (so its commits never fire NOTIFY), so this drives its own committing
    # connection instead.
    config = await dishka.get(DatabaseConfig)

    signal = PostgresOutboxSignal(config)
    await signal.start()
    writer = await _raw_connect(config)
    row_id = uuid7()
    try:
        # Let the listener establish its LISTEN, then arm past the connect-time
        # nudge so the wait below can only be woken by the trigger.
        await asyncio.sleep(0.3)
        signal.arm()

        await writer.execute(
            "INSERT INTO outbox_events (id, subject, payload) "
            "VALUES ($1, $2, $3::jsonb)",
            row_id,
            "test.signal",
            "{}",
        )

        # Wakes well within the timeout if the trigger fired; the outer wait_for
        # fails the test rather than hanging if it did not.
        await asyncio.wait_for(signal.wait(5), timeout=2)
    finally:
        # The insert really committed, so remove it — other outbox tests assert
        # on the set of unpublished rows and must not see this one.
        await writer.execute("DELETE FROM outbox_events WHERE id = $1", row_id)
        await writer.close()
        await signal.stop()
