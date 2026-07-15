from collections.abc import AsyncIterable

import httpx2
from dishka import Provider, Scope, provide

from fanfan.adapters.captcha.config import TurnstileConfig
from fanfan.adapters.captcha.turnstile import (
    NoOpCaptchaVerifier,
    TurnstileCaptchaVerifier,
)
from fanfan.adapters.config.models import EnvConfig
from fanfan.application.ports.captcha import CaptchaVerifier


class CaptchaProvider(Provider):
    scope = Scope.REQUEST

    @provide(scope=Scope.APP)
    def get_turnstile_config(self, config: EnvConfig) -> TurnstileConfig | None:
        return config.turnstile

    @provide
    async def get_captcha_verifier(
        self, config: TurnstileConfig | None
    ) -> AsyncIterable[CaptchaVerifier]:
        # No Turnstile config means captcha is disabled, so accept everything.
        if config is None:
            yield NoOpCaptchaVerifier()
            return

        async with httpx2.AsyncClient() as client:
            yield TurnstileCaptchaVerifier(config=config, client=client)
