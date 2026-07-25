from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from fanfan.adapters.config.parsers import get_config
from fanfan.common.version import APP_VERSION
from fanfan.core.exceptions.base import AppException
from fanfan.main.common import init
from fanfan.main.di import create_web_container
from fanfan.presentation.web.exceptions import (
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from fanfan.presentation.web.middlewares import (
    bind_request_context,
    no_store_cache_control,
    refresh_session_cookie,
)
from fanfan.presentation.web.openapi import API_TITLE, generate_operation_id
from fanfan.presentation.web.routes import setup_api_router


def create_app() -> FastAPI:
    init(service_name="web")

    config = get_config()
    app = FastAPI(
        debug=config.debug.enabled,
        title=API_TITLE,
        version=APP_VERSION,
        generate_unique_id_function=generate_operation_id,
    )

    setup_dishka(container=create_web_container(), app=app)

    app.middleware("http")(refresh_session_cookie(config.web))

    app.include_router(setup_api_router())

    # Handlers narrow `exc` to a concrete exception subtype, which Starlette's
    # broad `ExceptionHandler` signature doesn't model — a known false positive.
    app.add_exception_handler(AppException, app_exception_handler)  # ty: ignore[invalid-argument-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # ty: ignore[invalid-argument-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # ty: ignore[invalid-argument-type]
    # Catch-all for unanticipated errors so every response keeps the ErrorMessage
    # shape; more specific handlers above take precedence by exception type.
    app.add_exception_handler(Exception, unhandled_exception_handler)

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

    # Default-deny caching on every response, including CORS/error responses.
    app.middleware("http")(no_store_cache_control)

    # Registered last so it runs first (outermost): the request id is bound
    # before any other middleware or route handler, so all of their logs
    # carry it.
    app.middleware("http")(bind_request_context)

    return app
