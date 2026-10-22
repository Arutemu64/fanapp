from http import HTTPStatus
from typing import Any

import httpx2

from fanfan.adapters.tgbot.config import TelegramConfig

# https://core.telegram.org/bots/api#making-requests
_API_BASE_URL = "https://api.telegram.org"


class TelegramApiError(Exception):
    """The Bot API answered with a non-2xx status.

    ``status`` is the HTTP status, not the body's ``error_code``: Telegram
    documents ``error_code`` as "subject to change in the future", so callers
    branch on the status and read ``description`` only for logging.
    """

    def __init__(
        self, status: int, description: str, retry_after: int | None = None
    ) -> None:
        self.status = status
        self.description = description
        self.retry_after = retry_after
        super().__init__(f"Telegram API error {status}: {description}")


class TelegramApiClient:
    # Thin wrapper over a shared httpx2.AsyncClient, mirroring VkApiClient: the
    # pool is configured once in the DI provider (APP scope) and reused across
    # every send, so a notification burst keeps one TCP+TLS connection to
    # api.telegram.org. The bot token is a private detail here, not a
    # container-wide dependency.
    def __init__(self, client: httpx2.AsyncClient, config: TelegramConfig) -> None:
        self._client = client
        self._config = config

    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any],
    ) -> None:
        # The token has to travel in the URL path — the Bot API has no header
        # alternative — so httpx2's INFO request log would print it; see the
        # "httpx2" logger level in adapters/debug/logging.py.
        response = await self._client.post(
            f"{_API_BASE_URL}/bot{self._config.token.get_secret_value()}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": reply_markup,
            },
        )
        if response.is_success:
            return
        raise self._error_from(response)

    @staticmethod
    def _error_from(response: httpx2.Response) -> TelegramApiError:
        # A proxy or gateway in front of Telegram can answer with a non-JSON
        # body; the status alone still classifies the failure then.
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        retry_after = None
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            # https://core.telegram.org/bots/api#responseparameters
            retry_after = payload.get("parameters", {}).get("retry_after")
        return TelegramApiError(
            status=response.status_code,
            description=payload.get("description", response.reason_phrase),
            retry_after=retry_after,
        )
