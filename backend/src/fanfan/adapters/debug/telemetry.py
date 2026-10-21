import asyncio
from collections.abc import Callable
from typing import Any, cast

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx2 import Httpx2Integration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.types import Event

# Decides which exceptions are expected outcomes rather than bugs. Injected by
# the composition root, since that call belongs to the presentation layer's
# status mapping: a domain exception is expected when it maps to a status the
# client can act on, and a bug when it has no such marker.
ExpectedErrorPredicate = Callable[[BaseException], bool]

# uvicorn's own wording (uvicorn/server.py) when --timeout-graceful-shutdown
# expires: it logs the first at ERROR, then cancels each running request with
# the second as the CancelledError message. Open SSE streams never end on their
# own, so every deploy hits that timeout. It is how the API is meant to stop,
# not a fault, and would otherwise file two Sentry issues per deploy. A unit test
# pins both strings to the installed uvicorn so a bump that rewords them fails.
UVICORN_SHUTDOWN_TIMEOUT_LOG = (
    "Cancel %s running task(s), timeout graceful shutdown exceeded"
)
UVICORN_SHUTDOWN_CANCEL_MESSAGE = "Task cancelled, timeout graceful shutdown exceeded"


def _is_forced_shutdown(event: Event, exc_value: BaseException | None) -> bool:
    logentry = event.get("logentry") or {}
    if logentry.get("message") == UVICORN_SHUTDOWN_TIMEOUT_LOG:
        return True

    # Only a reported cancellation qualifies: an error raised while cleaning
    # up a cancelled request carries the cancellation as its context, and is a
    # real fault.
    if not isinstance(exc_value, asyncio.CancelledError):
        return False

    # The cancellation surfaces re-raised, so the message sits further down
    # the chain. Track what was seen: an exception chain can loop.
    seen: set[int] = set()
    while exc_value is not None and id(exc_value) not in seen:
        seen.add(id(exc_value))
        is_cancel = isinstance(exc_value, asyncio.CancelledError)
        if is_cancel and UVICORN_SHUTDOWN_CANCEL_MESSAGE in exc_value.args:
            return True
        exc_value = exc_value.__cause__ or exc_value.__context__
    return False


def _drop_expected_errors(
    event: Event, hint: dict[str, Any], is_expected_error: ExpectedErrorPredicate
) -> Event | None:
    exc_value = None
    if "exc_info" in hint:
        _, exc_value, _ = hint["exc_info"]
        if exc_value is not None and is_expected_error(exc_value):
            return None

    if _is_forced_shutdown(event, exc_value):
        return None

    return _scrub_sensitive_data(event)


def _scrub_sensitive_data(event: Event) -> Event:
    """Scrub potential PII from Sentry events before sending."""
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
    is_expected_error: ExpectedErrorPredicate,
    release: str | None = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.0,
) -> None:
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            # Commit SHA, matching the frontend's APP_BUILD, so an error
            # from either side of one deploy groups under the same release.
            # None leaves the SDK to its own detection, which finds nothing in
            # the image (no .git) — that is the local-build case.
            release=release,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            enable_logs=False,
            send_default_pii=False,
            before_send=lambda event, hint: _drop_expected_errors(
                event, hint, is_expected_error
            ),
            # Every integration is listed explicitly (even the ones that would
            # auto-enable from the installed package) so the observability
            # surface is auditable in one place instead of split between this
            # list and the SDK's auto-detection.
            integrations=[
                # Captures unhandled exceptions in detached asyncio tasks
                # (e.g. the SSE reader, the job worker's tasks) that
                # would otherwise escape the framework integrations. Unlike the
                # others here, this one is not auto-enabled, so it must be listed.
                AsyncioIntegration(),
                FastApiIntegration(failed_request_status_codes={*range(500, 600)}),
                # Spans every pooled query. Sentry has no psycopg 3 integration
                # (getsentry/sentry-python#2427), so the raw jobs LISTEN
                # connection goes untraced.
                SqlalchemyIntegration(),
                # Outbound-request spans for the httpx2 clients (OAuth, mail).
                Httpx2Integration(),
                RedisIntegration(),
            ],
        )
        sentry_sdk.set_tag("service", service_name)
