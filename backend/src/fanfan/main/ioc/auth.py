from authlib.integrations.starlette_client import OAuth
from dishka import Provider, Scope, provide

from fanfan.presentation.tgbot.config import TelegramConfig


class OAuthProvider(Provider):
    # APP scope, not REQUEST: Authlib caches the OIDC discovery document and
    # Telegram's JWKS on the registered client object itself. Rebuilding the
    # registry per request throws that cache away, costing three extra
    # round-trips to oauth.telegram.org per login (discovery on the redirect,
    # discovery + JWKS on the callback) and making Telegram's uptime a hard
    # dependency at both hops instead of one. Nothing request-scoped is stored
    # here — the per-flow OAuth state lives in the Starlette session cookie.
    scope = Scope.APP

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
                # PKCE is RECOMMENDED for confidential clients (RFC 9700 2.1.1)
                # and Telegram advertises S256 support. Authlib only generates a
                # code_verifier when this key is present; without it the flow
                # silently falls back to nonce-only code-injection protection.
                "code_challenge_method": "S256",
            },
        )
        return oauth
