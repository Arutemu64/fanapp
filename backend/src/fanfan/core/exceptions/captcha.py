from fanfan.core.exceptions.base import AccessDenied


# Failing the captcha is a form of access being denied (403); it keeps its own
# code so the frontend can show a captcha-specific message.
class CaptchaVerificationFailed(AccessDenied):
    code = "CAPTCHA_VERIFICATION_FAILED"
