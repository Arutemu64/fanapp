from dishka import Provider, Scope, provide
from pydantic import HttpUrl, SecretStr

from fanfan.presentation.web.config import WebConfig


class TestConfigProvider(Provider):
    """Provides the slice of app config the resolvable interactors need.

    The full ``EnvConfig`` is not built in tests (it pulls in NATS, Telegram,
    SMTP, etc., none of which are wired). Only ``WebConfig`` is required — the
    session store and the token registry read from it — so it is supplied here
    with fixed test values, the same way ``TestDbProvider`` supplies the DB and
    Redis configs.
    """

    scope = Scope.APP

    @provide
    def get_web_config(self) -> WebConfig:
        return WebConfig(
            host="localhost",
            port=8000,
            base_url=HttpUrl("http://localhost:8000/"),
            secret_key=SecretStr("test-secret-key"),
        )
