from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
    BindRequestContextMiddleware,
    CatchUnexpectedErrorsMiddleware,
    LimitRequestBodySizeMiddleware,
    NoStoreCacheControlMiddleware,
    RefreshSessionCookieMiddleware,
    SecurityHeadersMiddleware,
)
from fanfan.presentation.web.oauth import OAUTH_STATE_TTL_SECONDS
from fanfan.presentation.web.openapi import (
    API_TITLE,
    FanfanAPI,
    generate_operation_id,
)
from fanfan.presentation.web.routes import setup_api_router


def create_app() -> FastAPI:
    init(service_name="web")

    config = get_config()
    container = create_web_container()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await container.close()

    app = FanfanAPI(
        lifespan=lifespan,
        debug=config.debug.enabled,
        title=API_TITLE,
        version=APP_VERSION,
        generate_unique_id_function=generate_operation_id,
    )

    setup_dishka(container=container, app=app)

    app.add_middleware(RefreshSessionCookieMiddleware, web_config=config.web)

    app.add_middleware(CatchUnexpectedErrorsMiddleware)

    app.include_router(setup_api_router())

    add_exception_handlers(app)

    app.add_middleware(
        SessionMiddleware,
        secret_key=config.web.secret_key.get_secret_value(),
        max_age=OAUTH_STATE_TTL_SECONDS,
        same_site="lax",
        https_only=config.web.cookie_secure,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.web.cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(NoStoreCacheControlMiddleware)

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(LimitRequestBodySizeMiddleware)

    app.add_middleware(BindRequestContextMiddleware)

    return app
