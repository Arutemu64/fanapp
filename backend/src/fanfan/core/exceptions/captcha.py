from fanfan.core.exceptions.base import AccessDenied


class CaptchaVerificationFailed(AccessDenied):
    code = "CAPTCHA_VERIFICATION_FAILED"
