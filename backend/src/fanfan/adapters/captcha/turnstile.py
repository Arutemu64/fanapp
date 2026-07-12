import logging

import httpx2

from fanfan.adapters.captcha.config import TurnstileConfig
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed

logger = logging.getLogger(__name__)

# Cloudflare's server-side validation endpoint.
SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class TurnstileCaptchaVerifier(CaptchaVerifier):
    """Validates Turnstile tokens against Cloudflare's siteverify endpoint."""

    def __init__(self, config: TurnstileConfig, client: httpx2.AsyncClient):
        self.config = config
        self.client = client

    async def verify(self, token: str | None) -> None:
        if not token:
            # No token at all: the user never attempted the challenge. This is
            # rejected even during a Cloudflare outage (see fail-open below).
            raise CaptchaVerificationFailed

        payload = {
            "secret": self.config.secret_key.get_secret_value(),
            "response": token,
        }
        try:
            response = await self.client.post(SITEVERIFY_URL, data=payload)
        except httpx2.RequestError:
            # Cloudflare is unreachable (DNS / connection / timeout). Fail open:
            # a network blip or Cloudflare outage shouldn't lock everyone out of
            # login. The per-email rate lock still caps abuse in the meantime.
            logger.warning(
                "Turnstile siteverify unreachable; allowing request", exc_info=True
            )
            return

        if response.is_server_error:
            # A 5xx is an outage signal, not a verdict — fail open as above.
            logger.warning(
                "Turnstile siteverify returned %s; allowing request",
                response.status_code,
            )
            return

        # We got a real answer from Cloudflare, so honour its verdict.
        result = response.json()
        if not result.get("success", False):
            logger.warning(
                "Turnstile verification rejected: %s", result.get("error-codes")
            )
            raise CaptchaVerificationFailed


class NoOpCaptchaVerifier(CaptchaVerifier):
    """Accepts every token. Wired in when Turnstile is not configured."""

    async def verify(self, token: str | None) -> None:  # noqa: ARG002
        return None
