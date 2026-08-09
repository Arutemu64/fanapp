from collections.abc import AsyncIterable

import httpx2
from dishka import Provider, Scope, provide

from fanfan.adapters.captcha.config import SmartCaptchaConfig
from fanfan.adapters.captcha.yandex import (
    VALIDATE_TIMEOUT,
    NoOpCaptchaVerifier,
    SmartCaptchaVerifier,
)
from fanfan.adapters.config.models import EnvConfig
from fanfan.application.ports.captcha import CaptchaVerifier


class CaptchaProvider(Provider):
    scope = Scope.REQUEST

    @provide(scope=Scope.APP)
    def get_smartcaptcha_config(self, config: EnvConfig) -> SmartCaptchaConfig | None:
        return config.smartcaptcha

    @provide
    async def get_captcha_verifier(
        self, config: SmartCaptchaConfig | None
    ) -> AsyncIterable[CaptchaVerifier]:
        # No SmartCaptcha config means captcha is disabled, so accept everything.
        if config is None:
            yield NoOpCaptchaVerifier()
            return

        async with httpx2.AsyncClient(timeout=VALIDATE_TIMEOUT) as client:
            yield SmartCaptchaVerifier(config=config, client=client)
