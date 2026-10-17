from dishka import Provider, Scope, provide
from redis.asyncio import Redis

from fanfan.adapters.captcha.altcha import AltchaCaptchaVerifier, NoOpCaptchaVerifier
from fanfan.adapters.captcha.config import AltchaConfig
from fanfan.adapters.config.models import EnvConfig
from fanfan.application.ports.captcha import CaptchaVerifier


class CaptchaProvider(Provider):
    scope = Scope.APP

    @provide
    def get_altcha_config(self, config: EnvConfig) -> AltchaConfig | None:
        return config.altcha

    @provide
    def get_captcha_verifier(
        self, config: AltchaConfig | None, redis: Redis
    ) -> CaptchaVerifier:
        # No ALTCHA key means captcha is disabled, so accept everything.
        if config is None:
            return NoOpCaptchaVerifier()
        return AltchaCaptchaVerifier(config=config, redis=redis)
