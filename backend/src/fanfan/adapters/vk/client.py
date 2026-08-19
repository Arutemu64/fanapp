from typing import Any

import httpx2

from fanfan.adapters.vk.config import VkConfig

# Pin the API version so VK never falls back to an account-default that could
# change response shapes under us. 5.199 is the latest documented version in the
# official schema (VKCOM/vk-api-schema). https://dev.vk.ru/en/reference/versions
_VK_API_VERSION = "5.199"

# Every VK method hangs off this host. The vk.ru host is VK's post-rebrand
# domain; api.vk.com still resolves to the same API. https://dev.vk.ru/
_METHOD_BASE_URL = "https://api.vk.ru/method/"


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
    # Thin wrapper over a shared httpx2.AsyncClient, mirroring BaseApiClient: the
    # client (with its timeout) is configured once in the DI provider and reused
    # across every call, so a notification burst reuses the single TCP+TLS
    # connection to api.vk.ru instead of re-handshaking per message
    # (https://www.python-httpx.org/advanced/clients/). Provided at APP scope so
    # the pool outlives the per-message request scope; the group token is a
    # private detail here rather than a container-wide dependency.
    def __init__(self, client: httpx2.AsyncClient, config: VkConfig) -> None:
        self._client = client
        self._config = config

    async def _call_method(self, method: str, params: dict[str, Any]) -> Any:
        # Token and version travel in the POST body, not the query string, so the
        # group token never lands in access logs or the URL. VK still returns
        # HTTP 200 on a logical failure, carrying it in the body's `error` object.
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
        # Returns the id of the sent message so the caller can delete the group's
        # own copy afterwards. For a single peer_id VK answers with the bare
        # integer message id. https://dev.vk.ru/ru/method/messages.send
        return await self._call_method(
            "messages.send",
            {
                "peer_id": peer_id,
                "message": message,
                # random_id 0 disables VK's uniqueness check, so every send goes
                # through even when two notifications carry identical text; a
                # fixed non-zero value would instead let VK drop the second as a
                # duplicate. The outbox is the deduplication authority upstream.
                "random_id": 0,
            },
        )

    async def delete_message(self, *, message_id: int) -> None:
        # delete_for_all=0 removes the message only from the group's side of the
        # dialog: the notification stays in the user's inbox, while the group's
        # conversation list that organizers see is not cluttered by every send.
        # Unlike delete_for_all=1, this is not bound to the 24h-since-send window.
        # https://dev.vk.ru/ru/method/messages.delete
        await self._call_method(
            "messages.delete",
            {"message_ids": message_id, "delete_for_all": 0},
        )
