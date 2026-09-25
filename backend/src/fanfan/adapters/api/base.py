import asyncio
import email.utils
import logging
import random
from datetime import UTC, datetime
from typing import Any

import httpx2
from adaptix import Retort

logger = logging.getLogger(__name__)

# Every outbound call needs an explicit timeout: httpx2's 5s-on-every-operation
# default silently aborts a slow vendor page mid-sweep (the TicketsCloud
# ReadTimeout that motivated this). Read carries the generous budget because a
# full paginated sweep waits on the vendor's query; connect stays short so a
# genuinely unreachable host fails fast instead of hanging out the whole read.
DEFAULT_TIMEOUT = httpx2.Timeout(timeout=30.0, connect=10.0)

# Retry transient failures so one flaky page doesn't fail an otherwise healthy
# sweep. Every client call is an idempotent GET, so replay is safe. Backoff is
# exponential with jitter — the jitter keeps concurrent clients from retrying a
# struggling vendor in lockstep.
# Best practice: exponential backoff + jitter, retry only transient/idempotent
# failures (https://archman.dev/docs/distributed-systems-and-microservices/
# resilience-and-reliability-patterns/timeouts-retries-exponential-backoff-jitter).
MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 0.5
RETRY_MAX_DELAY = 10.0
# 429 and 5xx are the vendor asking us to back off or a transient outage. Other
# 4xx are the request's own fault and never improve on retry — 404 included,
# which TCloudClient.get_order relies on to surface as a normal "not found".
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
# A 429 or 503 may say how long to wait in Retry-After (RFC 9110 §10.2.3,
# https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after), and that hint
# beats our own guess. A hint longer than this means the vendor wants us gone
# for a while: give up and let the next scheduled sync try, rather than hold a
# sweep open for minutes.
RETRY_AFTER_MAX_DELAY = 60.0


class BaseApiClient:
    # Thin wrapper over an httpx2.AsyncClient that loads JSON responses into
    # plain dataclass DTOs via adaptix. The httpx2 client carries the base URL
    # and auth headers (configured in the DI provider), so subclasses only
    # declare endpoint methods. httpx2 raises httpx2.HTTPStatusError on non-2xx
    # responses (status available via error.response.status_code).
    def __init__(self, client: httpx2.AsyncClient, retort: Retort) -> None:
        self._client = client
        self._retort = retort

    async def _get[T](self, path: str, model: type[T], **params: Any) -> T:
        # `model` is the type adaptix loads into. Generic rather than `Any`, so
        # an endpoint method's declared return type is checked against what it
        # asks for here, instead of both ends agreeing to be unchecked.
        response = await self._request_with_retry(path, params)
        return self._retort.load(response.json(), model)

    async def _request_with_retry(
        self, path: str, params: dict[str, Any]
    ) -> httpx2.Response:
        attempt = 0
        while True:
            attempt += 1
            try:
                response = await self._client.get(path, params=params)
                response.raise_for_status()
            except (httpx2.TransportError, httpx2.HTTPStatusError) as error:
                if attempt >= MAX_ATTEMPTS or not _is_retryable(error):
                    raise
                delay = _retry_delay(error, attempt)
                if delay > RETRY_AFTER_MAX_DELAY:
                    raise
                logger.warning(
                    "Retrying vendor request after transient error",
                    extra={"path": path, "attempt": attempt, "delay": delay},
                    exc_info=error,
                )
                await asyncio.sleep(delay)
            else:
                return response


def _is_retryable(error: httpx2.TransportError | httpx2.HTTPStatusError) -> bool:
    if isinstance(error, httpx2.HTTPStatusError):
        return error.response.status_code in RETRYABLE_STATUS
    # Any TransportError: a connect/read/write/pool timeout or a network error.
    return True


def _retry_delay(
    error: httpx2.TransportError | httpx2.HTTPStatusError, attempt: int
) -> float:
    if isinstance(error, httpx2.HTTPStatusError):
        retry_after = _parse_retry_after(error.response.headers.get("Retry-After"))
        if retry_after is not None:
            return retry_after
    return _backoff_delay(attempt)


def _parse_retry_after(value: str | None) -> float | None:
    """Seconds to wait from a Retry-After header, or None if absent or unusable.

    Handles both RFC 9110 forms: delay-seconds ("120") and an HTTP-date.
    """
    if value is None:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)

    try:
        retry_at = email.utils.parsedate_to_datetime(value)
    except TypeError, ValueError:
        return None
    # An HTTP-date is always GMT, but a "-0000" zone parses as naive.
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    seconds = (retry_at - datetime.now(UTC)).total_seconds()
    return max(0.0, seconds)


def _backoff_delay(attempt: int) -> float:
    capped = min(RETRY_MAX_DELAY, RETRY_BASE_DELAY * 2 ** (attempt - 1))
    return float(capped * random.uniform(0.5, 1.5))  # noqa: S311 — jitter, not a draw
