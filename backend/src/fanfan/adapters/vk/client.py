from typing import Any

import httpx2

from fanfan.adapters.rate_limiter import RateLimiter
from fanfan.adapters.vk.config import VkConfig

_VK_API_VERSION = "5.199"

_METHOD_BASE_URL = "https://api.vk.ru/method/"

_REQUESTS_PER_SECOND = 18


class VkApiError(Exception):
    """A VK API method answered with an ``error`` object instead of a response.

    VK returns HTTP 200 even for logical failures, carrying the failure in the
    body's ``error`` object; ``code`` mirrors that ``error_code`` and drives the
    per-user vs. channel-wide translation in ``VkNotifier._handle_api_error``.
    """

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"VK API error {code}: {message}")


class VkApiClient:
    def __init__(self, client: httpx2.AsyncClient, config: VkConfig) -> None:
        self._client = client
        self._config = config
        self._rate_limiter = RateLimiter(per_second=_REQUESTS_PER_SECOND)

    async def _call_method(self, method: str, params: dict[str, Any]) -> Any:  # noqa: ANN401
        await self._rate_limiter.wait()
        response = await self._client.post(
            f"{_METHOD_BASE_URL}{method}",
            data={
                "access_token": self._config.group_token.get_secret_value(),
                "v": _VK_API_VERSION,
                **params,
            },
        )
        response.raise_for_status()
        payload = response.json()
        error = payload.get("error")
        if error is not None:
            raise VkApiError(
                code=error.get("error_code"),
                message=error.get("error_msg", ""),
            )
        return payload.get("response")

    async def send_message(self, *, peer_id: int, message: str) -> int:
        return int(
            await self._call_method(
                "messages.send",
                {
                    "peer_id": peer_id,
                    "message": message,
                    "random_id": 0,
                },
            )
        )

    async def delete_message(self, *, message_id: int) -> None:
        await self._call_method(
            "messages.delete",
            {"message_ids": message_id, "delete_for_all": 0},
        )
