import pytest

from fanfan.adapters.db.config import DatabaseConfig

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql+asyncpg://u:p@db:5432/fanfan",
        "postgresql://u:p@db:5432/fanfan",
    ],
)
def test_dsn_always_connects_through_psycopg(dsn: str) -> None:
    # The engine's connect args are psycopg-only, so a deployed DSN naming
    # another driver must still be routed through psycopg.
    config = DatabaseConfig(url=dsn)

    assert config.build_connection_str() == "postgresql+psycopg://u:p@db:5432/fanfan"


def test_connect_args_pin_utc_and_skip_disabled_timeouts() -> None:
    config = DatabaseConfig(
        url="postgresql+psycopg://u:p@db:5432/fanfan",
        statement_timeout=30000,
        lock_timeout=0,
        idle_in_transaction_session_timeout=60000,
        application_name="api",
    )

    assert config.build_connect_args() == {
        "options": (
            "-c TimeZone=UTC -c statement_timeout=30000 "
            "-c idle_in_transaction_session_timeout=60000"
        ),
        "application_name": "api",
    }
