import json

from authlib.integrations.starlette_client import OAuth
from authlib.oauth2.client import OAuth2Client
from dishka import Provider, Scope, provide

from fanfan.adapters.config.models import EnvConfig


def _vk_compliance_fix(session: OAuth2Client) -> None:
    """Strip ``id_token`` from VK ID's token response.

    VK ID may return an ``id_token`` alongside the access token, but it does
    not publish a JWKS endpoint, so Authlib cannot validate it. Removing it
    before Authlib processes the response prevents a validation failure.
    """

    def _strip_id_token(resp):  # type: ignore[no-untyped-def]
        token = resp.json()
        token.pop("id_token", None)
        resp._content = json.dumps(token).encode("utf-8")  # noqa: SLF001
        return resp

    session.register_compliance_hook("access_token_response", _strip_id_token)


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
    def get_oauth(self, config: EnvConfig) -> OAuth:
        oauth = OAuth()
        # Telegram OAuth
        oauth.register(  # pyright: ignore[reportUnknownMemberType]
            name="telegram",
            client_id=config.bot.client_id,
            client_secret=config.bot.client_secret.get_secret_value(),
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
        # VK ID OAuth (optional — absent when VK__CLIENT_ID is not set)
        if config.vk:
            oauth.register(  # pyright: ignore[reportUnknownMemberType]
                name="vk",
                client_id=config.vk.client_id,
                client_secret=config.vk.client_secret.get_secret_value(),
                authorize_url="https://id.vk.ru/authorize",
                access_token_url="https://id.vk.ru/oauth2/auth",  # noqa: S106
                token_endpoint_auth_method="client_secret_post",  # noqa: S106
                client_kwargs={
                    "scope": "vkid.personal_info email",
                    "code_challenge_method": "S256",
                },
                compliance_fix=_vk_compliance_fix,
            )
        return oauth
