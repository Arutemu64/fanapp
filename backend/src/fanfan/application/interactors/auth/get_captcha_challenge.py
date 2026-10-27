import logging

from pydantic import BaseModel

from fanfan.application.dto.captcha import CaptchaChallengeDTO
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.application.ports.rate_limiter import RateLimiter
from fanfan.core.exceptions.rate_limit import (
    TooManyAttempts,
    TooManyLoginCodeRequests,
)

logger = logging.getLogger(__name__)

CAPTCHA_CHALLENGE_IP_MAX_REQUESTS = 60
CAPTCHA_CHALLENGE_IP_WINDOW_SECONDS = 600


class GetCaptchaChallengeInput(BaseModel):
    client_ip: str | None = None


class GetCaptchaChallenge:
    def __init__(
        self, captcha_verifier: CaptchaVerifier, rate_limiter: RateLimiter
    ) -> None:
        self.captcha_verifier = captcha_verifier
        self.rate_limiter = rate_limiter

    async def __call__(self, data: GetCaptchaChallengeInput) -> CaptchaChallengeDTO:
        if data.client_ip:
            await self._register_ip_attempt(data.client_ip)
        challenge = await self.captcha_verifier.issue_challenge()
        return CaptchaChallengeDTO(challenge=challenge)

    async def _register_ip_attempt(self, client_ip: str) -> None:
        try:
            await self.rate_limiter.hit(
                f"captcha_challenge:ip:{client_ip}",
                limit=CAPTCHA_CHALLENGE_IP_MAX_REQUESTS,
                window_seconds=CAPTCHA_CHALLENGE_IP_WINDOW_SECONDS,
            )
        except TooManyAttempts as e:
            logger.warning(
                "Captcha challenge blocked: too many requests",
                extra={"client_ip": client_ip},
            )
            raise TooManyLoginCodeRequests(retry_after=e.details["retry_after"]) from e
