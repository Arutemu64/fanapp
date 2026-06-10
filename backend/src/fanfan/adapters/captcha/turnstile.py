import logging

import httpx

from fanfan.adapters.captcha.config import TurnstileConfig
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed

logger = logging.getLogger(__name__)

# Cloudflare's server-side validation endpoint.
SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileCaptchaVerifier:
    """Validates Turnstile tokens against Cloudflare's siteverify endpoint."""

    def __init__(self, config: TurnstileConfig, client: httpx.AsyncClient):
        self.config = config
        self.client = client

    async def verify(self, token: str | None) -> None:
        if not token:
            raise CaptchaVerificationFailed

        payload = {
            "secret": self.config.secret_key.get_secret_value(),
            "response": token,
        }
        try:
            response = await self.client.post(SITEVERIFY_URL, data=payload)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            # Fail closed: if we cannot reach Cloudflare we reject the request
            # rather than let a bot through. Logged so outages are visible.
            logger.exception("Turnstile siteverify request failed")
            raise CaptchaVerificationFailed from e

        if not result.get("success", False):
            logger.warning(
                "Turnstile verification rejected: %s", result.get("error-codes")
            )
            raise CaptchaVerificationFailed


class NoOpCaptchaVerifier:
    """Accepts every token. Wired in when Turnstile is not configured."""

    async def verify(self, token: str | None) -> None:  # noqa: ARG002
        return None
