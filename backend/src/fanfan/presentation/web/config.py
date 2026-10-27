from urllib.parse import urlencode, urlsplit

from pydantic import BaseModel, HttpUrl, SecretStr, field_validator

from fanfan.core.vo.social_identity import SocialProvider


class WebConfig(BaseModel):
    host: str
    port: int

    public_url: HttpUrl
    secret_key: SecretStr

    cors_allow_origins: list[str] = []

    cookie_secure: bool = False
    session_ttl_seconds: int = 60 * 60 * 24 * 30
    session_touch_threshold_seconds: int = 60 * 60 * 6

    enabled_oauth_providers: list[SocialProvider] = [SocialProvider.VK]

    @field_validator("enabled_oauth_providers", mode="after")
    @classmethod
    def _dedupe_oauth_providers(
        cls, value: list[SocialProvider]
    ) -> list[SocialProvider]:
        """Drop duplicates while preserving order.

        The frontend renders this list with a keyed `{#each provider}` (login
        screen and profile card), so a repeated id — a config typo like
        `["vk","vk"]` — would collide those keys and break the render. Normalising
        to a unique list protects every consumer, and is gentler than refusing to
        boot over a harmless typo.
        """
        seen: set[SocialProvider] = set()
        unique: list[SocialProvider] = []
        for provider in value:
            if provider not in seen:
                seen.add(provider)
                unique.append(provider)
        return unique

    @field_validator("public_url", mode="after")
    @classmethod
    def ensure_trailing_slash(cls, value: HttpUrl) -> HttpUrl:
        """Normalize the URL to end with `/` so build_url() can concatenate.

        Pydantic already does this for a bare host, but not for a sub-path
        deploy: `https://example.com/app` stays slashless, which would make
        build_url("/link") yield `https://example.com/applink`.
        """
        url = value.unicode_string()
        if url.endswith("/"):
            return value
        return HttpUrl(f"{url}/")

    def cors_origins(self) -> list[str]:
        """Explicit list of allowed browser origins for CORS.

        Falls back to the origin (scheme + host + port) taken from public_url
        so a standard single-origin deploy needs no extra config.
        """
        if self.cors_allow_origins:
            return self.cors_allow_origins
        parts = urlsplit(self.public_url.unicode_string())
        return [f"{parts.scheme}://{parts.netloc}"]

    def build_url(self, path: str, query_params: dict[str, str] | None = None) -> str:
        url = f"{self.public_url.unicode_string()}{path.removeprefix('/')}"
        if query_params is None:
            return url
        return f"{url}?{urlencode(query_params)}"
