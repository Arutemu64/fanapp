from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response

from fanfan.adapters.config.parsers import get_config
from fanfan.core.exceptions.base import AppException
from fanfan.main.common import init
from fanfan.main.di import create_web_container
from fanfan.presentation.web.exceptions import (
    app_exception_handler,
    auth_exception_handler,
    validation_exception_handler,
)
from fanfan.presentation.web.middlewares import bind_request_context
from fanfan.presentation.web.routes import setup_api_router
from fanfan.presentation.web.routes.auth.cookies import set_auth_cookie


def create_app() -> FastAPI:
    init(service_name="web")

    config = get_config()
    app = FastAPI(debug=config.debug.enabled)

    setup_dishka(container=create_web_container(), app=app)

    @app.middleware("http")
    async def refresh_session_cookie_middleware(
        request: Request,
        call_next,
    ) -> Response:
        response = await call_next(request)
        session_id: str | None = getattr(request.state, "renew_session_id", None)
        if session_id:
            set_auth_cookie(response, session_id, config.web)
        return response

    app.include_router(setup_api_router())

    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore  # noqa: PGH003
    app.add_exception_handler(HTTPException, auth_exception_handler)  # type: ignore  # noqa: PGH003
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore  # noqa: PGH003

    # This session cookie holds the Telegram OAuth state/nonce (authlib). Mark it
    # Secure only when the rest of the app is (cookie_secure), so a plain-HTTP
    # deploy can still complete the OAuth flow — a Secure cookie is never sent
    # back over HTTP, which would break the login callback. Keep it True in prod.
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.web.secret_key.get_secret_value(),
        same_site="lax",
        https_only=config.web.cookie_secure,
    )

    app.add_middleware(
        CORSMiddleware,
        # Explicit origins (never "*") because requests carry the session
        # cookie — a wildcard with credentials would trust every site.
        allow_origins=config.web.cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registered last so it runs first (outermost): the request id is bound
    # before any other middleware or route handler, so all of their logs
    # carry it.
    app.middleware("http")(bind_request_context)

    return app
