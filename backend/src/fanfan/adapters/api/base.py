from typing import Any

import httpx
from adaptix import Retort


class BaseApiClient:
    # Thin wrapper over an httpx.AsyncClient that loads JSON responses into
    # plain dataclass DTOs via adaptix. The httpx client carries the base URL
    # and auth headers (configured in the DI provider), so subclasses only
    # declare endpoint methods. httpx raises httpx.HTTPStatusError on non-2xx
    # responses (status available via error.response.status_code).
    def __init__(self, client: httpx.AsyncClient, retort: Retort):
        self._client = client
        self._retort = retort

    async def _get(self, path: str, model: Any, **params: Any) -> Any:
        # `model` is a type hint (e.g. Order or list[Request]); the caller's
        # public method annotates the concrete return type, so adaptix-loaded
        # results stay correctly typed at the call site.
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return self._retort.load(response.json(), model)
