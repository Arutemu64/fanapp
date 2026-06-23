from fastapi import Response

from fanfan.presentation.web.config import WebConfig

SESSION_COOKIE_NAME = "session_id"


def set_auth_cookie(response: Response, session_id: str, config: WebConfig) -> None:
    """Persist session identifier in an HttpOnly cookie for browser requests."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        max_age=config.session_ttl_seconds,
        samesite="lax",
        secure=config.cookie_secure,
        path="/",
    )


def delete_auth_cookie(response: Response) -> None:
    """Clear auth cookies using the same path that was used on set."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
