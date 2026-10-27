import base64
import json

import pytest
from altcha import Challenge, Payload, solve_challenge
from dishka import AsyncContainer
from pydantic import SecretStr
from redis.asyncio import Redis

from fanfan.adapters.captcha.altcha import (
    CHALLENGE_COUNTER_MAX,
    CHALLENGE_COUNTER_MIN,
    AltchaCaptchaVerifier,
)
from fanfan.adapters.captcha.config import AltchaConfig
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def make_verifier(dishka_request: AsyncContainer) -> AltchaCaptchaVerifier:
    redis = await dishka_request.get(Redis)
    return AltchaCaptchaVerifier(
        config=AltchaConfig(hmac_key=SecretStr("test-hmac-key")), redis=redis
    )


async def solve(verifier: AltchaCaptchaVerifier) -> str:
    challenge = Challenge.from_dict(await verifier.issue_challenge())
    solution = solve_challenge(challenge)
    assert solution is not None
    return Payload(challenge, solution).to_base64()


async def test_solved_challenge_passes_once(dishka_request: AsyncContainer) -> None:
    verifier = await make_verifier(dishka_request)
    token = await solve(verifier)

    await verifier.verify(token)

    with pytest.raises(CaptchaVerificationFailed):
        await verifier.verify(token)


async def test_challenge_signed_with_another_key_is_rejected(
    dishka_request: AsyncContainer,
) -> None:
    verifier = await make_verifier(dishka_request)
    redis = await dishka_request.get(Redis)
    forger = AltchaCaptchaVerifier(
        config=AltchaConfig(hmac_key=SecretStr("attacker-key")), redis=redis
    )

    with pytest.raises(CaptchaVerificationFailed):
        await verifier.verify(await solve(forger))


async def test_tampered_challenge_is_rejected(dishka_request: AsyncContainer) -> None:
    verifier = await make_verifier(dishka_request)
    payload = json.loads(base64.b64decode(await solve(verifier)))
    payload["challenge"]["parameters"]["expiresAt"] += 3600
    tampered = base64.b64encode(json.dumps(payload).encode()).decode()

    with pytest.raises(CaptchaVerificationFailed):
        await verifier.verify(tampered)


@pytest.mark.parametrize("token", [None, "", "not-base64!", "e30="])
async def test_missing_or_malformed_token_is_rejected(
    dishka_request: AsyncContainer, token: str | None
) -> None:
    verifier = await make_verifier(dishka_request)

    with pytest.raises(CaptchaVerificationFailed):
        await verifier.verify(token)


async def test_challenge_makes_the_client_find_the_issued_counter(
    dishka_request: AsyncContainer,
) -> None:
    verifier = await make_verifier(dishka_request)
    challenge = Challenge.from_dict(await verifier.issue_challenge())

    solution = solve_challenge(challenge)
    assert solution is not None
    assert CHALLENGE_COUNTER_MIN <= solution.counter <= CHALLENGE_COUNTER_MAX
    assert challenge.parameters.key_signature is not None
