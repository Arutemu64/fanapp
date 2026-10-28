import asyncio
from collections.abc import Callable
from typing import Any, cast

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx2 import Httpx2Integration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.types import Event

from fanfan.adapters.debug.redaction import redact_secret_paths

ExpectedErrorPredicate = Callable[[BaseException], bool]

UVICORN_SHUTDOWN_TIMEOUT_LOG = (
    "Cancel %s running task(s), timeout graceful shutdown exceeded"
)
UVICORN_SHUTDOWN_CANCEL_MESSAGE = "Task cancelled, timeout graceful shutdown exceeded"


def _is_forced_shutdown(event: Event, exc_value: BaseException | None) -> bool:
    logentry = event.get("logentry") or {}
    if logentry.get("message") == UVICORN_SHUTDOWN_TIMEOUT_LOG:
        return True

    if not isinstance(exc_value, asyncio.CancelledError):
        return False

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
    """Scrub potential PII and secret URL segments from Sentry events."""
    request = event.get("request", {})
    url = request.get("url")
    if isinstance(url, str):
        request["url"] = redact_secret_paths(url)

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


def setup_telemetry(  # noqa: PLR0913, PLR0917
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
            release=release,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            enable_logs=False,
            send_default_pii=False,
            before_send=lambda event, hint: _drop_expected_errors(
                event, hint, is_expected_error
            ),
            # Sampled transactions carry the request URL too.
            before_send_transaction=lambda event, _hint: _scrub_sensitive_data(event),
            integrations=[
                AsyncioIntegration(),
                FastApiIntegration(failed_request_status_codes={*range(500, 600)}),
                SqlalchemyIntegration(),
                Httpx2Integration(),
            ],
        )
        sentry_sdk.set_tag("service", service_name)
