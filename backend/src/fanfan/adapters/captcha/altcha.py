import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from altcha import Payload, create_challenge, verify_solution
from redis.asyncio import Redis

from fanfan.adapters.captcha.config import AltchaConfig
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed

logger = logging.getLogger(__name__)

# PBKDF2 runs natively in every browser through WebCrypto, so no WASM solver is
# shipped. cost is the PBKDF2 iteration count per attempt; the default keyPrefix
# "00" makes the solver try ~256 counters on average. Together they are the
# difficulty knob: raise them if bots get through, lower them if phones at the
# venue solve too slowly.
CHALLENGE_ALGORITHM = "PBKDF2/SHA-256"
CHALLENGE_COST = 5_000
# Long enough for someone to type an email after the client pre-solves on page
# load; the replay guard keeps each spent challenge for exactly this long.
CHALLENGE_TTL = timedelta(minutes=10)


class AltchaCaptchaVerifier(CaptchaVerifier):
    """Self-hosted ALTCHA proof-of-work: issues HMAC-signed challenges and
    verifies solutions locally, with no third-party call.
    """

    def __init__(self, config: AltchaConfig, redis: Redis) -> None:
        self.config = config
        self.redis = redis

    async def issue_challenge(self) -> dict[str, Any]:
        # Not the deterministic `counter` mode ALTCHA also offers: that pre-solves
        # every challenge on the server, so each anonymous GET would cost us the
        # same PBKDF2 work it is meant to cost the client.
        challenge = create_challenge(
            algorithm=CHALLENGE_ALGORITHM,
            cost=CHALLENGE_COST,
            expires_at=datetime.now(UTC) + CHALLENGE_TTL,
            hmac_secret=self.config.hmac_key.get_secret_value(),
        )
        return challenge.to_dict()

    async def verify(self, token: str | None) -> None:
        if not token:
            raise CaptchaVerificationFailed

        # verify_solution parses the raw token itself and reports malformed input
        # as unverified, so untrusted bytes never reach our own parsing.
        result = verify_solution(token, self.config.hmac_key.get_secret_value())
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
        verification, so unverified garbage cannot fill Redis, and with SET NX,
        so two concurrent submits of the same payload cannot both pass.
        """
        # verify_solution has already proven both are present and signed by us.
        signature = payload.challenge.signature
        expires_at = payload.challenge.parameters.expires_at
        first_use = await self.redis.set(
            f"captcha:altcha:spent:{signature}", 1, nx=True, exat=expires_at
        )
        if not first_use:
            logger.warning("Captcha verification rejected: challenge replayed")
            raise CaptchaVerificationFailed


class NoOpCaptchaVerifier(CaptchaVerifier):
    """Accepts every token. Wired in when ALTCHA is not configured."""

    async def issue_challenge(self) -> None:
        return None

    async def verify(self, token: str | None) -> None:  # noqa: ARG002
        return None
