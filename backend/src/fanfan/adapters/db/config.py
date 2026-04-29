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
    echo: bool = True

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
