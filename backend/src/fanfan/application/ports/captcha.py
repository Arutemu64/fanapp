from typing import Protocol


class CaptchaVerifier(Protocol):
    """Verifies a captcha token solved by the user before a sensitive action.

    Implementations either call an external captcha service (e.g. Cloudflare
    Turnstile) or accept everything when captcha is disabled. Keeping this as a
    port lets the application layer stay unaware of which one is wired in.
    """

    async def verify(self, token: str | None) -> None:
        """Validate a captcha ``token``.

        Raises CaptchaVerificationFailed when the token is missing, malformed,
        or rejected by the captcha service. Returns ``None`` on success.
        """
        ...
