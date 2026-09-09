from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed


class FakeCaptchaVerifier(CaptchaVerifier):
    """Records verified tokens instead of calling Yandex SmartCaptcha.

    Accepts everything by default (captcha effectively disabled), matching the
    NoOpCaptchaVerifier the app wires in when no SmartCaptcha config is present.
    Set ``reject = True`` to make ``verify`` raise, so a test can exercise the
    captcha-rejection branch without an external service.
    """

    def __init__(self) -> None:
        self.verified_tokens: list[str | None] = []
        self.reject = False

    async def verify(self, token: str | None) -> None:
        self.verified_tokens.append(token)
        if self.reject:
            raise CaptchaVerificationFailed
