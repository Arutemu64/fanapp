import asyncio
from uuid import uuid7

import psycopg
import pytest
from dishka import AsyncContainer
from sqlalchemy.engine import make_url

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.job_signal import PostgresJobSignal

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _raw_connect(config: DatabaseConfig) -> psycopg.AsyncConnection:
    url = make_url(config.build_connection_str())
    return await psycopg.AsyncConnection.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        dbname=url.database,
        autocommit=True,
    )


async def test_insert_trigger_wakes_the_listener(dishka: AsyncContainer) -> None:
    # End-to-end over a real database: the migration's AFTER INSERT trigger must
    # pg_notify on the exact channel the adapter LISTENs on, or notifications
    # would silently fall back to poll-only latency. The per-test session rolls
    # back (so its commits never fire NOTIFY), so this drives its own committing
    # connection instead.
    config = await dishka.get(DatabaseConfig)

    signal = PostgresJobSignal(config)
    await signal.start()
    writer = await _raw_connect(config)
    row_id = uuid7()
    try:
        # Let the listener establish its LISTEN, then arm past the connect-time
        # nudge so the wait below can only be woken by the trigger.
        await asyncio.sleep(0.3)
        signal.arm()

        await writer.execute(
            "INSERT INTO jobs (id, name, payload) VALUES (%s, %s, %s::jsonb)",
            (row_id, "test.signal", "{}"),
        )

        # Wakes well within the timeout if the trigger fired; the outer wait_for
        # fails the test rather than hanging if it did not.
        await asyncio.wait_for(signal.wait(5), timeout=2)
    finally:
        # The insert really committed, so remove it — other tests assert on
        # the set of queued jobs and must not see this one.
        await writer.execute("DELETE FROM jobs WHERE id = %s", (row_id,))
        await writer.close()
        await signal.stop()
