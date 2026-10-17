from typing import Any, Protocol


class CaptchaVerifier(Protocol):
    """Issues captcha challenges and verifies their solutions before a sensitive
    action.

    Implementations either run a real captcha (ALTCHA proof-of-work) or accept
    everything when captcha is disabled. Keeping this as a port lets the
    application layer stay unaware of which one is wired in.
    """

    async def issue_challenge(self) -> dict[str, Any] | None:
        """Return a fresh challenge for the client to solve, or ``None`` when
        captcha is disabled and the client should send no token at all.

        The challenge is opaque to the application: the client hands it to the
        provider's solver unchanged.
        """
        ...

    async def verify(self, token: str | None) -> None:
        """Validate a captcha ``token``.

        Raises CaptchaVerificationFailed when the token is missing, malformed,
        expired, already spent, or otherwise rejected. Returns ``None`` on
        success.
        """
        ...
