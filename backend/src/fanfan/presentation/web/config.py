from urllib.parse import urlencode, urlsplit

from pydantic import BaseModel, HttpUrl, SecretStr, field_validator


class WebConfig(BaseModel):
    # Where the process binds — not how the outside world reaches it.
    host: str
    port: int

    # Public origin browsers use to reach the app (frontend at `/`, API at
    # `/api`). The app cannot infer this from host/port behind a reverse proxy,
    # and deriving it from the request Host header would allow link poisoning,
    # so it is configured explicitly.
    public_url: HttpUrl
    secret_key: SecretStr

    # Browser origins allowed to make credentialed CORS requests to the API.
    # Leave empty to default to the origin derived from public_url.
    # Never use "*" here: the browser sends the session cookie with requests.
    cors_allow_origins: list[str] = []

    # Set to True in production (HTTPS). Ensures cookies are never sent over plain HTTP.
    cookie_secure: bool = False
    # Redis-backed session lifetime in seconds.
    session_ttl_seconds: int = 60 * 60 * 24 * 30
    # Refresh Redis TTL only when remaining time drops below this threshold.
    session_touch_threshold_seconds: int = 60 * 60 * 6

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
