from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from fanfan.adapters.config.parsers import get_config
from fanfan.common.version import APP_VERSION
from fanfan.main.common import init
from fanfan.main.di import create_web_container
from fanfan.presentation.web.exceptions import add_exception_handlers
from fanfan.presentation.web.middlewares import (
    bind_request_context,
    catch_unexpected_errors,
    limit_request_body_size,
    no_store_cache_control,
    refresh_session_cookie,
    security_headers,
)
from fanfan.presentation.web.oauth import OAUTH_STATE_TTL_SECONDS
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

    # Registered early so it sits inside every middleware below (the last one
    # registered runs outermost): an unanticipated route error becomes a 500 that
    # still passes through CORS, caching, security and request-id middleware.
    app.middleware("http")(catch_unexpected_errors)

    app.include_router(setup_api_router())

    add_exception_handlers(app)

    # This session cookie holds the Telegram OAuth state/nonce (authlib). Secure
    # tracks cookie_secure so a plain-HTTP deploy can still complete the OAuth
    # flow — a Secure cookie is never sent back over HTTP.
    #
    # max_age replaces Starlette's 14-day default with Authlib's own state TTL,
    # the budget for one consent round-trip: don't shorten it, or a slow
    # Telegram confirmation could fail here while Authlib still accepts the state.
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.web.secret_key.get_secret_value(),
        max_age=OAUTH_STATE_TTL_SECONDS,
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

    # Hardening headers (nosniff, anti-framing, referrer policy) on every
    # response, so the API stays secure-by-default behind any proxy.
    app.middleware("http")(security_headers)

    # Reject an oversized body by Content-Length before anything reads it, so
    # the app is not solely dependent on the reverse proxy's own cap.
    app.middleware("http")(limit_request_body_size)

    # Registered last so it runs first (outermost): the request id is bound
    # before any other middleware or route handler, so all of their logs
    # carry it.
    app.middleware("http")(bind_request_context)

    return app
