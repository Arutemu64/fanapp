from urllib.parse import urlencode, urlsplit

from pydantic import BaseModel, HttpUrl, SecretStr


class WebConfig(BaseModel):
    host: str
    port: int

    base_url: HttpUrl
    secret_key: SecretStr

    # Browser origins allowed to make credentialed CORS requests to the API.
    # Leave empty to default to the frontend origin derived from base_url.
    # Never use "*" here: the browser sends the session cookie with requests.
    cors_allow_origins: list[str] = []

    # Set to True in production (HTTPS). Ensures cookies are never sent over plain HTTP.
    cookie_secure: bool = False
    # Redis-backed session lifetime in seconds.
    session_ttl_seconds: int = 60 * 60 * 24 * 30
    # Refresh Redis TTL only when remaining time drops below this threshold.
    session_touch_threshold_seconds: int = 60 * 60 * 6

    def cors_origins(self) -> list[str]:
        """Explicit list of allowed browser origins for CORS.

        Falls back to the frontend origin (scheme + host + port) taken from
        base_url so a standard single-frontend deploy needs no extra config.
        """
        if self.cors_allow_origins:
            return self.cors_allow_origins
        parts = urlsplit(self.base_url.unicode_string())
        return [f"{parts.scheme}://{parts.netloc}"]

    def build_url(self, path: str, query_params: dict[str, str] | None = None) -> str:
        # `WEB__BASE_URL` is expected to include a trailing slash already.
        url = f"{self.base_url.unicode_string()}{path.removeprefix('/')}"
        if query_params is None:
            return url
        return f"{url}?{urlencode(query_params)}"
