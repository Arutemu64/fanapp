from typing import cast

import sentry_sdk
from fastapi.exceptions import RequestValidationError
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.types import Event

from fanfan.core.exceptions.base import AppException


def _is_asyncpg_teardown_timeout(exc_value: BaseException) -> bool:
    """Recognise the benign asyncpg connection-teardown TimeoutError.

    SQLAlchemy's asyncpg dialect closes an invalidated or recycled connection
    by awaiting `_terminate_graceful_close` under `asyncio.shield` (needed here
    by `pool_pre_ping` + `pool_recycle`). When the driving greenlet is cancelled
    or moves on, the shield keeps that coroutine running as an orphaned task; its
    2s graceful-close timeout then fires with nobody awaiting it, so the
    `TimeoutError` surfaces via the event loop's exception handler as an
    unhandled asyncio error (mechanism=asyncio, handled=false). The doomed
    connection is discarded regardless — the request that borrowed the pool has
    already succeeded — so this is teardown noise, not a request failure, and it
    cannot be caught in app code. See sqlalchemy/sqlalchemy#13338.
    """
    if not isinstance(exc_value, TimeoutError):
        return False
    tb = exc_value.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        if (
            frame.f_code.co_name == "_terminate_graceful_close"
            and frame.f_globals.get("__name__")
            == "sqlalchemy.dialects.postgresql.asyncpg"
        ):
            return True
        tb = tb.tb_next
    return False


def _scrub_sensitive_data(event: Event, hint: dict) -> Event | None:
    """Scrub potential PII from Sentry events before sending."""
    # Filter out domain business exceptions and request validation exceptions
    if "exc_info" in hint:
        _, exc_value, _ = hint["exc_info"]
        if isinstance(exc_value, (AppException, RequestValidationError)):
            return None
        if _is_asyncpg_teardown_timeout(exc_value):
            return None

    if event.get("request", {}).get("headers"):
        headers = cast("dict[str, str]", event["request"]["headers"])
        sensitive = ["cookie", "authorization", "x-api-key", "x-auth-token"]
        for key in list(headers.keys()):
            if key.lower() in sensitive:
                headers[key] = "[Filtered]"

    if event.get("user"):
        user = event["user"]
        allowed_keys = {"id", "username"}
        for key in list(user.keys()):
            if key not in allowed_keys:
                del user[key]

    return event


def setup_telemetry(  # noqa: PLR0913, PLR0917 — one parameter per Sentry knob
    service_name: str,
    environment: str,
    sentry_dsn: str | None,
    release: str | None = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.0,
) -> None:
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            # Commit SHA, matching the frontend's SENTRY_RELEASE, so an error
            # from either side of one deploy groups under the same release.
            # None leaves the SDK to its own detection, which finds nothing in
            # the image (no .git) — that is the local-build case.
            release=release,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            enable_logs=False,
            send_default_pii=False,
            before_send=_scrub_sensitive_data,
            integrations=[
                # Captures unhandled exceptions in detached asyncio tasks
                # (e.g. SSE fan-out, scheduler/stream background work) that
                # would otherwise escape the framework integrations.
                AsyncioIntegration(),
                FastApiIntegration(failed_request_status_codes={*range(500, 600)}),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
        )
        sentry_sdk.set_tag("service", service_name)
