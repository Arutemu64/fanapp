from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from fanfan.adapters.config.parsers import get_config
from fanfan.common.version import APP_VERSION
from fanfan.main.common import init
from fanfan.main.di import create_web_container
from fanfan.presentation.web.config import WebConfig
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
    API_CONTACT,
    API_DESCRIPTION,
    API_TITLE,
    FanfanAPI,
    generate_operation_id,
)
from fanfan.presentation.web.routes import setup_api_router


def create_app() -> FastAPI:
    init(service_name="web")

    config = get_config()
    return build_app(create_web_container(), config.web, debug=config.debug.enabled)


def build_app(
    container: AsyncContainer, web_config: WebConfig, *, debug: bool = False
) -> FastAPI:
    """Assemble the app around a ready container.

    Split from `create_app` so the HTTP tests run the real middleware stack
    on their own container (docs/testing.md "HTTP tests").
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        await container.close()

    app = FanfanAPI(
        lifespan=lifespan,
        debug=debug,
        title=API_TITLE,
        description=API_DESCRIPTION,
        contact=API_CONTACT,
        version=APP_VERSION,
        generate_unique_id_function=generate_operation_id,
    )

    setup_dishka(container=container, app=app)

    app.add_middleware(RefreshSessionCookieMiddleware, web_config=web_config)

    app.add_middleware(CatchUnexpectedErrorsMiddleware)

    app.include_router(setup_api_router())

    add_exception_handlers(app)

    app.add_middleware(
        SessionMiddleware,
        secret_key=web_config.secret_key.get_secret_value(),
        max_age=OAUTH_STATE_TTL_SECONDS,
        same_site="lax",
        https_only=web_config.cookie_secure,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=web_config.cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(NoStoreCacheControlMiddleware)

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(LimitRequestBodySizeMiddleware)

    app.add_middleware(BindRequestContextMiddleware)

    return app
