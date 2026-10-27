import asyncio
from uuid import uuid7

import psycopg
import pytest
from dishka import AsyncContainer
from sqlalchemy.engine import make_url

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.outbox_signal import PostgresOutboxSignal

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
    config = await dishka.get(DatabaseConfig)

    signal = PostgresOutboxSignal(config)
    await signal.start()
    writer = await _raw_connect(config)
    row_id = uuid7()
    try:
        await asyncio.sleep(0.3)
        signal.arm()

        await writer.execute(
            "INSERT INTO outbox_events (id, subject, payload) "
            "VALUES (%s, %s, %s::jsonb)",
            (row_id, "test.signal", "{}"),
        )

        await asyncio.wait_for(signal.wait(5), timeout=2)
    finally:
        await writer.execute("DELETE FROM outbox_events WHERE id = %s", (row_id,))
        await writer.close()
        await signal.stop()
