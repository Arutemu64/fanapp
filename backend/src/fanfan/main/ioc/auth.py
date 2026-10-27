import json

import httpx2
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

    def _strip_id_token(resp: httpx2.Response) -> httpx2.Response:
        token = resp.json()
        token.pop("id_token", None)
        resp._content = json.dumps(token).encode("utf-8")  # noqa: SLF001
        return resp

    session.register_compliance_hook("access_token_response", _strip_id_token)


class OAuthProvider(Provider):
    scope = Scope.APP

    @provide
    def get_oauth(self, config: EnvConfig) -> OAuth:
        oauth = OAuth()
        oauth.register(  # pyright: ignore[reportUnknownMemberType]
            name="telegram",
            client_id=config.bot.client_id,
            client_secret=config.bot.client_secret.get_secret_value(),
            server_metadata_url="https://oauth.telegram.org/.well-known/openid-configuration",
            client_kwargs={
                "scope": "openid profile telegram:bot_access",
                "code_challenge_method": "S256",
            },
        )
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
