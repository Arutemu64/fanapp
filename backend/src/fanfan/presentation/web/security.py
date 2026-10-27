from fastapi import Security
from fastapi.security import APIKeyCookie

from fanfan.presentation.web.routes.auth.cookies import SESSION_COOKIE_NAME

_session_cookie_scheme = APIKeyCookie(
    name=SESSION_COOKIE_NAME,
    scheme_name="SessionCookie",
    auto_error=False,
    description=(
        "Session cookie set after login. "
        "Documentation only; enforced in the application layer."
    ),
)

session_security = Security(_session_cookie_scheme)
