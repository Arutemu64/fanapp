import hashlib
import hmac
import logging
import math
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, override

from altcha import Payload, create_challenge, verify_solution

from fanfan.adapters.captcha.config import AltchaConfig
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.application.ports.cooldown import Cooldown
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed
from fanfan.core.exceptions.rate_limit import CooldownActive

logger = logging.getLogger(__name__)

CHALLENGE_ALGORITHM = "PBKDF2/SHA-256"
CHALLENGE_COST = 5_000
CHALLENGE_COUNTER_MIN = 500
CHALLENGE_COUNTER_MAX = 1_000
CHALLENGE_TTL = timedelta(minutes=10)


class AltchaCaptchaVerifier(CaptchaVerifier):
    """Self-hosted ALTCHA proof-of-work: issues HMAC-signed challenges and
    verifies solutions locally, with no third-party call.
    """

    def __init__(self, config: AltchaConfig, cooldown: Cooldown) -> None:
        self.cooldown = cooldown
        master = config.hmac_key.get_secret_value().encode()
        self._challenge_secret = _subkey(master, b"challenge-signature")
        self._key_secret = _subkey(master, b"derived-key-signature")

    @override
    async def issue_challenge(self) -> dict[str, Any]:
        counter = CHALLENGE_COUNTER_MIN + secrets.randbelow(
            CHALLENGE_COUNTER_MAX - CHALLENGE_COUNTER_MIN + 1
        )
        challenge = create_challenge(
            algorithm=CHALLENGE_ALGORITHM,
            cost=CHALLENGE_COST,
            counter=counter,
            expires_at=datetime.now(UTC) + CHALLENGE_TTL,
            hmac_secret=self._challenge_secret,
            hmac_key_secret=self._key_secret,
        )
        return challenge.to_dict()

    @override
    async def verify(self, token: str | None) -> None:
        if not token:
            raise CaptchaVerificationFailed

        result = verify_solution(
            token, self._challenge_secret, hmac_key_secret=self._key_secret
        )
        if not result.verified:
            logger.warning(
                "Captcha verification rejected",
                extra={
                    "expired": result.expired,
                    "invalid_signature": result.invalid_signature,
                    "invalid_solution": result.invalid_solution,
                },
            )
            raise CaptchaVerificationFailed

        await self._spend(Payload.from_base64(token))

    async def _spend(self, payload: Payload) -> None:
        """Accept each solved challenge once.

        A valid solution stays cryptographically valid until it expires, so
        without this a bot solves one challenge and replays it for every request
        (https://altcha.org/docs/v2/cloud/integrate). Recorded only after
        verification, so unverified garbage cannot fill the store. A cooldown
        claim lasting until the challenge expires admits exactly one of two
        concurrent submits of the same payload.
        """
        signature = payload.challenge.signature
        try:
            async with self.cooldown.claim(
                f"captcha:altcha:spent:{signature}", _seconds_left(payload)
            ):
                pass
        except CooldownActive as e:
            logger.warning("Captcha verification rejected: challenge replayed")
            raise CaptchaVerificationFailed from e


def _seconds_left(payload: Payload) -> int:
    expires_at = payload.challenge.parameters.expires_at
    if expires_at is None:
        return int(CHALLENGE_TTL.total_seconds())
    return max(1, math.ceil(expires_at - datetime.now(UTC).timestamp()))


def _subkey(master: bytes, purpose: bytes) -> str:
    return hmac.new(master, purpose, hashlib.sha256).hexdigest()


class NoOpCaptchaVerifier(CaptchaVerifier):
    """Accepts every token. Wired in when ALTCHA is not configured."""

    @override
    async def issue_challenge(self) -> None:
        return None

    @override
    async def verify(self, token: str | None) -> None:
        return None
