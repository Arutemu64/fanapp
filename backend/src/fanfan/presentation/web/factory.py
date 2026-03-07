import typing
from contextlib import asynccontextmanager

import logfire
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from fanfan.adapters.config.models import EnvConfig
from fanfan.adapters.config.parsers import get_config
from fanfan.core.exceptions.auth import UserNotAuthenticated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.main.common import init
from fanfan.main.di import create_web_container
from fanfan.presentation.web.admin import setup_admin
from fanfan.presentation.web.exceptions import (
    access_denied_handler,
    auth_exception_handler,
    user_not_authenticated_handler,
)
from fanfan.presentation.web.routes import setup_api_router

if typing.TYPE_CHECKING:
    from dishka import AsyncContainer


@asynccontextmanager
async def lifespan(app: FastAPI):
    container: AsyncContainer = app.state.dishka_container

    # Setup admin
    config = await container.get(EnvConfig)
    setup_admin(
        app=app, config=config, session_pool=await container.get(async_sessionmaker)
    )

    yield
    await app.state.dishka_container.close()


def create_app() -> FastAPI:
    # Init
    init(service_name="web")

    # Setup FastAPI app
    config = get_config()
    app = FastAPI(lifespan=lifespan, debug=config.debug.enabled)

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
