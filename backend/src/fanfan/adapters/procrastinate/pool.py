from psycopg_pool import AsyncConnectionPool

from fanfan.adapters.db.config import DatabaseConfig


def create_job_pool(config: DatabaseConfig, max_size: int) -> AsyncConnectionPool:
    """The worker's pool for Procrastinate's own queries (fetch, finish, retry).

    Separate from the SQLAlchemy engine, which the tasks' interactors use. The
    same libpq parameters apply, so the safety timeouts and the
    ``application_name`` label cover these connections too. Procrastinate opens
    its LISTEN connection from this pool's settings, outside the pool itself.
    """
    return AsyncConnectionPool(
        conninfo=config.build_libpq_dsn(),
        kwargs=config.build_connect_args(),
        min_size=1,
        max_size=max_size,
        open=False,
        # Replaces a connection the server dropped instead of handing it out.
        check=AsyncConnectionPool.check_connection,
    )
