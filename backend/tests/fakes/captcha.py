from typing import Any

from fanfan.application.ports.captcha import CaptchaVerifier
from fanfan.core.exceptions.captcha import CaptchaVerificationFailed


class FakeCaptchaVerifier(CaptchaVerifier):
    """Records verified tokens instead of running ALTCHA proof-of-work.

    Accepts everything by default (captcha effectively disabled), matching the
    NoOpCaptchaVerifier the app wires in when no ALTCHA config is present.
    Set ``reject = True`` to make ``verify`` raise, so a test can exercise the
    captcha-rejection branch without solving a real challenge.
    """

    def __init__(self) -> None:
        self.verified_tokens: list[str | None] = []
        self.reject = False

    async def issue_challenge(self) -> dict[str, Any] | None:
        return None

    async def verify(self, token: str | None) -> None:
        self.verified_tokens.append(token)
        if self.reject:
            raise CaptchaVerificationFailed
