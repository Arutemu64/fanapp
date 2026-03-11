import logfire
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from fanfan.adapters.config.parsers import get_config
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.main.common import init
from fanfan.main.di import create_web_container
from fanfan.presentation.web.exceptions import (
    access_denied_handler,
    auth_exception_handler,
    user_not_authenticated_handler,
)
from fanfan.presentation.web.routes import setup_api_router


def create_app() -> FastAPI:
    # Init
    init(service_name="web")

    # Setup FastAPI app
    config = get_config()
    app = FastAPI(debug=config.debug.enabled)

    @app.get("/debug")
    async def debug(request: Request):
        return {
            "url": str(request.url),
            "scheme": request.url.scheme,
            "headers": dict(request.headers),
        }

    # Setup DI
    setup_dishka(container=create_web_container(), app=app)

    # Include routers
    app.include_router(setup_api_router())

    # Register error handlers
    app.add_exception_handler(AccessDenied, access_denied_handler)
    app.add_exception_handler(UserNotAuthenticated, user_not_authenticated_handler)
    app.add_exception_handler(HTTPException, auth_exception_handler)

    # Setup FastAPI middlewares
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.web.secret_key.get_secret_value(),
        same_site="lax",
        https_only=True,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Instrument with Logfire
    logfire.instrument_fastapi(app)

    return app
