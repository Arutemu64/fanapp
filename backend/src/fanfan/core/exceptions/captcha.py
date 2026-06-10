from fanfan.core.exceptions.base import AppException


class CaptchaVerificationFailed(AppException):
    code = "CAPTCHA_VERIFICATION_FAILED"
