from collections.abc import AsyncIterable

import httpx2
from dishka import Provider, Scope, provide

from fanfan.adapters.captcha.turnstile import (
    NoOpCaptchaVerifier,
    TurnstileCaptchaVerifier,
)
from fanfan.adapters.config.models import EnvConfig
from fanfan.application.ports.captcha import CaptchaVerifier


class CaptchaProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def get_captcha_verifier(
        self, config: EnvConfig
    ) -> AsyncIterable[CaptchaVerifier]:
        # No Turnstile config means captcha is disabled, so accept everything.
        if config.turnstile is None:
            yield NoOpCaptchaVerifier()
            return

        async with httpx2.AsyncClient() as client:
            yield TurnstileCaptchaVerifier(config=config.turnstile, client=client)
