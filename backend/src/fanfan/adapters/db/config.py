from pydantic import BaseModel, PostgresDsn, SecretStr, model_validator
from sqlalchemy.engine import make_url


class DatabaseConfig(BaseModel):
    url: PostgresDsn | None = None

    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: SecretStr | None = None
    name: str | None = None

    database_system: str = "postgresql"
    driver: str = "psycopg"
    echo: bool = False

    pool_size: int = 5
    max_overflow: int = 10
    pool_recycle: int = 1800

    statement_timeout: int = 30000
    lock_timeout: int = 10000
    idle_in_transaction_session_timeout: int = 60000

    application_name: str | None = None

    def build_connect_args(self) -> dict[str, str]:
        """libpq connection parameters for every pooled connection.

        Timeouts set to 0 are omitted so Postgres keeps its own default
        (unlimited) rather than being handed a redundant "0".
        """
        settings = ["-c TimeZone=UTC"]
        timeouts = {
            "statement_timeout": self.statement_timeout,
            "lock_timeout": self.lock_timeout,
            "idle_in_transaction_session_timeout": (
                self.idle_in_transaction_session_timeout
            ),
        }
        for name, value in timeouts.items():
            if value > 0:
                settings.append(f"-c {name}={value}")
        connect_args = {"options": " ".join(settings)}
        if self.application_name is not None:
            connect_args["application_name"] = self.application_name
        return connect_args

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
            url = make_url(self.url.unicode_string())
            url = url.set(drivername=f"{self.database_system}+{self.driver}")
            return url.render_as_string(hide_password=False)

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
