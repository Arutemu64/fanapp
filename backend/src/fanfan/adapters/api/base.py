import asyncio
import email.utils
import logging
import random
from datetime import UTC, datetime
from typing import Any

import httpx2
from adaptix import Retort

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx2.Timeout(timeout=30.0, connect=10.0)

MAX_ATTEMPTS = 3
RETRY_BASE_DELAY = 0.5
RETRY_MAX_DELAY = 10.0
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
RETRY_AFTER_MAX_DELAY = 60.0


class BaseApiClient:
    def __init__(self, client: httpx2.AsyncClient, retort: Retort) -> None:
        self._client = client
        self._retort = retort

    async def _get[T](self, path: str, model: type[T], **params: Any) -> T:
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
    return True


def _retry_delay(
    error: httpx2.TransportError | httpx2.HTTPStatusError, attempt: int
) -> float:
    if isinstance(error, httpx2.HTTPStatusError):
        retry_after = _parse_retry_after(error.response.headers.get("Retry-After"))
        if retry_after is not None:
            return retry_after
    capped = min(RETRY_MAX_DELAY, RETRY_BASE_DELAY * 2 ** (attempt - 1))
    return float(capped * random.uniform(0.5, 1.5))  # noqa: S311


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
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    seconds = (retry_at - datetime.now(UTC)).total_seconds()
    return max(0.0, seconds)
