from pydantic import BaseModel, NatsDsn, SecretStr

# nats-py's default gives up after 60 reconnect attempts 2 s apart, about two
# minutes, and then closes the connection for good. Nothing reopens it, so a
# longer NATS outage would leave the process running but cut off from NATS, and
# Compose does not restart a container for failing its healthcheck. A negative
# value retries forever.
# https://docs.nats.io/using-nats/developer/connecting/reconnect/max
MAX_RECONNECT_ATTEMPTS = -1


class NatsConfig(BaseModel):
    host: str
    port: int
    user: str
    password: SecretStr

    def build_connection_str(self) -> str:
        dsn: NatsDsn = NatsDsn.build(
            scheme="nats",
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password.get_secret_value(),
        )
        return dsn.unicode_string()
