import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.auth.get_captcha_challenge import (
    CAPTCHA_CHALLENGE_IP_MAX_REQUESTS,
    GetCaptchaChallenge,
    GetCaptchaChallengeInput,
)
from fanfan.core.exceptions.rate_limit import TooManyLoginCodeRequests

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_get_captcha_challenge_caps_requests_per_ip(
    dishka_request: AsyncContainer,
) -> None:
    interactor = await dishka_request.get(GetCaptchaChallenge)

    for _ in range(CAPTCHA_CHALLENGE_IP_MAX_REQUESTS):
        await interactor(GetCaptchaChallengeInput(client_ip="203.0.113.9"))

    with pytest.raises(TooManyLoginCodeRequests):
        await interactor(GetCaptchaChallengeInput(client_ip="203.0.113.9"))

    # Another address behind its own IP is unaffected.
    await interactor(GetCaptchaChallengeInput(client_ip="203.0.113.10"))
