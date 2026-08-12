import httpx2

from fanfan.adapters.vk.config import VkConfig

# Pin the API version so VK never falls back to an account-default that could
# change response shapes under us. 5.199 is the latest documented version in the
# official schema (VKCOM/vk-api-schema). https://dev.vk.ru/en/reference/versions
_VK_API_VERSION = "5.199"

# messages.send is the only method this client calls. Full URL rather than a
# base_url + relative path because the client owns the single endpoint. The
# vk.ru host is VK's post-rebrand domain; api.vk.com still resolves to the same
# API. https://dev.vk.ru/ru/method/messages.send
_MESSAGES_SEND_URL = "https://api.vk.ru/method/messages.send"


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
    # across every send, so a notification burst reuses the single TCP+TLS
    # connection to api.vk.ru instead of re-handshaking per message
    # (https://www.python-httpx.org/advanced/clients/). Provided at APP scope so
    # the pool outlives the per-message request scope; the group token is a
    # private detail here rather than a container-wide dependency.
    def __init__(self, client: httpx2.AsyncClient, config: VkConfig) -> None:
        self._client = client
        self._config = config

    async def send_message(self, *, peer_id: int, message: str) -> None:
        # Token and version travel in the POST body, not the query string, so the
        # group token never lands in access logs or the URL. VK still returns
        # HTTP 200 on a logical failure, carrying it in the body's `error` object.
        response = await self._client.post(
            _MESSAGES_SEND_URL,
            data={
                "access_token": self._config.group_token.get_secret_value(),
                "v": _VK_API_VERSION,
                "peer_id": peer_id,
                "message": message,
                # random_id 0 disables VK's uniqueness check, so every send goes
                # through even when two notifications carry identical text; a
                # fixed non-zero value would instead let VK drop the second as a
                # duplicate. The outbox is the deduplication authority upstream.
                "random_id": 0,
            },
        )
        response.raise_for_status()
        error = response.json().get("error")
        if error is not None:
            raise VkApiError(
                code=error.get("error_code"),
                message=error.get("error_msg", ""),
            )
