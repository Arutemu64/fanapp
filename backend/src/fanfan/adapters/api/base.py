import asyncio
import logging
import random
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


class BaseApiClient:
    # Thin wrapper over an httpx2.AsyncClient that loads JSON responses into
    # plain dataclass DTOs via adaptix. The httpx2 client carries the base URL
    # and auth headers (configured in the DI provider), so subclasses only
    # declare endpoint methods. httpx2 raises httpx2.HTTPStatusError on non-2xx
    # responses (status available via error.response.status_code).
    def __init__(self, client: httpx2.AsyncClient, retort: Retort):
        self._client = client
        self._retort = retort

    async def _get(self, path: str, model: Any, **params: Any) -> Any:
        # `model` is a type hint (e.g. Order or list[Request]); the caller's
        # public method annotates the concrete return type, so adaptix-loaded
        # results stay correctly typed at the call site.
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
                logger.warning(
                    "Retrying vendor request after transient error",
                    extra={"path": path, "attempt": attempt},
                    exc_info=error,
                )
                await asyncio.sleep(_backoff_delay(attempt))
            else:
                return response


def _is_retryable(error: httpx2.TransportError | httpx2.HTTPStatusError) -> bool:
    if isinstance(error, httpx2.HTTPStatusError):
        return error.response.status_code in RETRYABLE_STATUS
    # Any TransportError: a connect/read/write/pool timeout or a network error.
    return True


def _backoff_delay(attempt: int) -> float:
    capped = min(RETRY_MAX_DELAY, RETRY_BASE_DELAY * 2 ** (attempt - 1))
    return capped * random.uniform(0.5, 1.5)  # noqa: S311 — jitter, not a security draw
