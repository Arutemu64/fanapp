from urllib.parse import urlencode

from pydantic import BaseModel, HttpUrl, SecretStr


class WebConfig(BaseModel):
    host: str
    port: int

    base_url: HttpUrl
    path: str = "/"
    secret_key: SecretStr
    jwt_issuer: str = "fanapp-api"
    jwt_audience: str = "fanapp-web"

    # Set to True in production (HTTPS). Ensures cookies are never sent over plain HTTP.
    cookie_secure: bool = False
    # Redis-backed session lifetime in seconds.
    session_ttl_seconds: int = 60 * 60 * 24 * 30
    # Refresh Redis TTL only when remaining time drops below this threshold.
    session_touch_threshold_seconds: int = 60 * 60 * 6

    def build_url(self, path: str, query_params: dict[str, str] | None = None) -> str:
        # `WEB__BASE_URL` is expected to include a trailing slash already.
        url = f"{self.base_url.unicode_string()}{path.removeprefix('/')}"
        if query_params is None:
            return url
        return f"{url}?{urlencode(query_params)}"
