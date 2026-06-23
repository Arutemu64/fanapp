from fastapi import Security
from fastapi.security import APIKeyCookie

from fanfan.presentation.web.routes.auth.cookies import SESSION_COOKIE_NAME

# Documentation-only security scheme. Declares the session cookie so OpenAPI and
# Swagger render a lock icon + "Authorize" on protected routes. auto_error=False
# means it never raises at runtime; real enforcement stays in the application
# layer (CurrentUserProvider.require_user). The scheme is still emitted into the
# OpenAPI spec regardless of auto_error, which is exactly what we want here.
_session_cookie_scheme = APIKeyCookie(
    name=SESSION_COOKIE_NAME,
    scheme_name="SessionCookie",
    auto_error=False,
    description="Session cookie set after login.",
)

# Attach via route/router `dependencies=[require_session_docs]`. The resolved
# value is intentionally unused; its presence is what registers the scheme and
# the per-operation security requirement in OpenAPI.
require_session_docs = Security(_session_cookie_scheme)
