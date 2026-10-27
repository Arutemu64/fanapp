from dishka import Provider, Scope, provide

from fanfan.adapters.captcha.altcha import AltchaCaptchaVerifier, NoOpCaptchaVerifier
from fanfan.adapters.captcha.config import AltchaConfig
from fanfan.adapters.config.models import EnvConfig
from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.application.ports.cooldown import Cooldown


class CaptchaProvider(Provider):
    scope = Scope.APP

    @provide
    def get_altcha_config(self, config: EnvConfig) -> AltchaConfig | None:
        return config.altcha

    @provide(scope=Scope.REQUEST)
    def get_captcha_verifier(
        self, config: AltchaConfig | None, cooldown: Cooldown
    ) -> CaptchaVerifier:
        if config is None:
            return NoOpCaptchaVerifier()
        return AltchaCaptchaVerifier(config=config, cooldown=cooldown)
