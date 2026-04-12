from fastapi import Response

from fanfan.adapters.auth.jwt import ACCESS_TOKEN_TTL, REFRESH_TOKEN_TTL
from fanfan.presentation.web.config import WebConfig

# Keep cookie max-age synchronized with JWT TTL constants.
ACCESS_TOKEN_MAX_AGE = int(ACCESS_TOKEN_TTL.total_seconds())
REFRESH_TOKEN_MAX_AGE = int(REFRESH_TOKEN_TTL.total_seconds())


def set_auth_cookies(
    response: Response, access_token: str, refresh_token: str, config: WebConfig
) -> None:
    """Persist auth tokens in HttpOnly cookies for browser + SSR flows."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_MAX_AGE,
        samesite="lax",
        secure=config.cookie_secure,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=REFRESH_TOKEN_MAX_AGE,
        samesite="lax",
        secure=config.cookie_secure,
        path="/",
    )


def delete_auth_cookies(response: Response) -> None:
    """Clear auth cookies using the same path that was used on set."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
