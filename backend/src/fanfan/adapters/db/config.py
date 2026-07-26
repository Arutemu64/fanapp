from pydantic import BaseModel, PostgresDsn, SecretStr, model_validator


class DatabaseConfig(BaseModel):
    url: PostgresDsn | None = None

    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: SecretStr | None = None
    name: str | None = None

    database_system: str = "postgresql"
    driver: str = "asyncpg"
    # Defaults off: echo logs every statement *and* its bound parameters, so a
    # deployment whose .env loses DB__ECHO would quietly start writing emails and
    # password hashes to the logs. `extra="ignore"` means that drift never fails
    # at boot, so the safe value has to be the default. Dev opts in.
    echo: bool = False

    # Connection pool sizing (SQLAlchemy QueuePool). A single process may open up
    # to pool_size + max_overflow connections. Kept explicit so the three
    # long-lived services (api, faststream, scheduler), each with its own engine,
    # stay well under Postgres' default max_connections=100.
    pool_size: int = 5
    max_overflow: int = 10
    # Recycle connections older than this many seconds, guarding against a VPS
    # firewall or Postgres silently dropping connections that sit idle too long.
    pool_recycle: int = 1800

    # Server-side safety timeouts (milliseconds), applied as asyncpg
    # server_settings on every connection. They bound the blast radius of a
    # runaway query or a transaction left open across an await: a tripped timeout
    # raises instead of pinning a pooled connection (and any locks it holds)
    # forever. Defaults are generous enough for the batch deletes the outbox and
    # notification relays run. Set to 0 to disable an individual timeout.
    statement_timeout: int = 30000
    lock_timeout: int = 10000
    idle_in_transaction_session_timeout: int = 60000

    # Labels connections in pg_stat_activity so you can tell which service holds a
    # lock. Overridden per service in Docker Compose; None keeps asyncpg's default.
    application_name: str | None = None

    def build_server_settings(self) -> dict[str, str]:
        """asyncpg server_settings (all values must be strings).

        Timeouts set to 0 are omitted so Postgres keeps its own default
        (unlimited) rather than being handed a redundant "0".
        """
        settings: dict[str, str] = {}
        timeouts = {
            "statement_timeout": self.statement_timeout,
            "lock_timeout": self.lock_timeout,
            "idle_in_transaction_session_timeout": (
                self.idle_in_transaction_session_timeout
            ),
        }
        for name, value in timeouts.items():
            if value > 0:
                settings[name] = str(value)
        if self.application_name is not None:
            settings["application_name"] = self.application_name
        return settings

    @model_validator(mode="after")
    def validate_url_or_parts(self) -> DatabaseConfig:
        if self.url is not None:
            return self

        missing_fields = [
            field
            for field in ("host", "port", "user", "password", "name")
            if getattr(self, field) is None
        ]
        if missing_fields:
            msg = (
                "DatabaseConfig requires either url or all connection fields: "
                + ", ".join(missing_fields)
            )
            raise ValueError(msg)

        return self

    def build_connection_str(self) -> str:
        if self.url is not None:
            return self.url.unicode_string()

        if (
            self.host is None
            or self.port is None
            or self.user is None
            or self.password is None
            or self.name is None
        ):
            msg = "DatabaseConfig is missing connection fields"
            raise ValueError(msg)

        dsn: PostgresDsn = PostgresDsn.build(
            scheme=f"{self.database_system}+{self.driver}",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            path=self.name,
        )
        return dsn.unicode_string()
