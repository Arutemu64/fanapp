from typing import cast

import sentry_sdk
from fastapi.exceptions import RequestValidationError
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.types import Event

from fanfan.core.exceptions.base import AppException


def _scrub_sensitive_data(event: Event, hint: dict) -> Event | None:
    """Scrub potential PII from Sentry events before sending."""
    # Filter out domain business exceptions and request validation exceptions
    if "exc_info" in hint:
        _, exc_value, _ = hint["exc_info"]
        if isinstance(exc_value, (AppException, RequestValidationError)):
            return None

    # Scrub request headers
    if event.get("request", {}).get("headers"):
        headers = cast("dict[str, str]", event["request"]["headers"])
        sensitive = ["cookie", "authorization", "x-api-key", "x-auth-token"]
        for key in list(headers.keys()):
            if key.lower() in sensitive:
                headers[key] = "[Filtered]"

    # Scrub user data — keep only id and username, remove emails
    if event.get("user"):
        user = event["user"]
        allowed_keys = {"id", "username"}
        for key in list(user.keys()):
            if key not in allowed_keys:
                del user[key]

    return event


def setup_telemetry(
    service_name: str,
    environment: str,
    sentry_dsn: str | None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.0,
) -> None:
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
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
