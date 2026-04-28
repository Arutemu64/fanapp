from authlib.integrations.starlette_client import OAuth
from dishka import Provider, Scope, provide

from fanfan.presentation.tgbot.config import TelegramConfig


class OAuthProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_oauth(self, config: TelegramConfig) -> OAuth:
        oauth = OAuth()
        # Telegram OAuth
        oauth.register(  # pyright: ignore[reportUnknownMemberType]
            name="telegram",
            client_id=config.client_id,
            client_secret=config.client_secret.get_secret_value(),
            server_metadata_url="https://oauth.telegram.org/.well-known/openid-configuration",
            client_kwargs={
                "scope": "openid profile telegram:bot_access",
            },
        )
        return oauth
