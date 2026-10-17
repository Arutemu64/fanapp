from fanfan.application.dto.captcha import CaptchaChallengeDTO
from fanfan.application.ports.captcha import CaptchaVerifier


class GetCaptchaChallenge:
    def __init__(self, captcha_verifier: CaptchaVerifier) -> None:
        self.captcha_verifier = captcha_verifier

    async def __call__(self) -> CaptchaChallengeDTO:
        challenge = await self.captcha_verifier.issue_challenge()
        return CaptchaChallengeDTO(challenge=challenge)
