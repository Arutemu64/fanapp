import logging

import httpx2

from fanfan.adapters.captcha.config import SmartCaptchaConfig
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed

logger = logging.getLogger(__name__)

VALIDATE_URL = "https://smartcaptcha.cloud.yandex.ru/validate"

# This call sits on the interactive login path and fails open (see verify), so
# the budget is tight on purpose: a slow or hung Yandex must let login through
# fast rather than stall it. Deliberately much shorter than the vendor-sync
# clients' generous DEFAULT_TIMEOUT, which serve slow background sweeps.
VALIDATE_TIMEOUT = httpx2.Timeout(3.0, connect=2.0)


class SmartCaptchaVerifier(CaptchaVerifier):
    """Validates SmartCaptcha tokens against Yandex's validate endpoint."""

    def __init__(self, config: SmartCaptchaConfig, client: httpx2.AsyncClient):
        self.config = config
        self.client = client

    async def verify(self, token: str | None) -> None:
        if not token:
            # No token at all: the user never attempted the challenge. This is
            # rejected even during an outage (see fail-open below).
            raise CaptchaVerificationFailed

        payload = {
            "secret": self.config.server_key.get_secret_value(),
            "token": token,
        }
        try:
            response = await self.client.post(VALIDATE_URL, data=payload)
        except httpx2.RequestError:
            # SmartCaptcha is unreachable (DNS / connection / timeout). Fail open:
            # a network blip or Yandex outage shouldn't lock everyone out of
            # login. The per-email rate lock still caps abuse in the meantime.
            logger.warning(
                "SmartCaptcha validate unreachable; allowing request", exc_info=True
            )
            return

        if response.is_server_error:
            # A 5xx is an outage signal, not a verdict — fail open as above.
            logger.warning(
                "SmartCaptcha validate returned %s; allowing request",
                response.status_code,
            )
            return

        # We got a real answer from Yandex, so honour its verdict. A human passes
        # with status "ok"; anything else ("failed", incl. reused/expired tokens)
        # is a rejection.
        result = response.json()
        if result.get("status") != "ok":
            logger.warning(
                "SmartCaptcha verification rejected: %s", result.get("message")
            )
            raise CaptchaVerificationFailed


class NoOpCaptchaVerifier(CaptchaVerifier):
    """Accepts every token. Wired in when SmartCaptcha is not configured."""

    async def verify(self, token: str | None) -> None:  # noqa: ARG002
        return None
