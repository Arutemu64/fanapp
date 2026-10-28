from http import HTTPStatus
from typing import Any

import httpx2

from fanfan.adapters.tgbot.config import TelegramConfig

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
        response = await self._client.post(
            f"{_API_BASE_URL}/bot{self._config.token.get_secret_value()}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                # The link lives in the button; a preview card would repeat it.
                "link_preview_options": {"is_disabled": True},
                "reply_markup": reply_markup,
            },
        )
        if response.is_success:
            return
        raise self._error_from(response)

    @staticmethod
    def _error_from(response: httpx2.Response) -> TelegramApiError:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        retry_after = None
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = payload.get("parameters", {}).get("retry_after")
        return TelegramApiError(
            status=response.status_code,
            description=payload.get("description", response.reason_phrase),
            retry_after=retry_after,
        )
