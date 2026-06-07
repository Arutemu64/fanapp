from typing import Protocol

from fanfan.core.vo.user import UserId


class TokenRegistry(Protocol):
    """Stores short-lived one-time email codes.

    Contract for every implementation:
      - Codes are kept hashed, never in plain text, so a storage dump does
        not reveal valid codes.
      - Issuing a new code for a target revokes the previously issued one,
        so only the newest code is ever valid.
      - Consuming the correct code deletes it (single use).
      - Each target is locked out after ``max_attempts`` wrong guesses within
        ``window_seconds`` by raising ``TooManyOtpAttempts``; this is what
        stops brute-forcing the short numeric code.
    """

    async def issue_email_confirmation_code(
        self,
        user_id: UserId,
        email: str,
        code: str,
        ttl_seconds: int,
    ) -> None: ...

    async def consume_email_confirmation_code(
        self,
        user_id: UserId,
        code: str,
        max_attempts: int,
        window_seconds: int,
    ) -> str | None:
        """Return the confirmed email on success, ``None`` on a wrong code.

        Raises ``TooManyOtpAttempts`` once the user is over ``max_attempts``.
        """
        ...

    async def issue_email_login_code(
        self,
        user_id: UserId,
        email: str,
        code: str,
        ttl_seconds: int,
    ) -> None: ...

    async def consume_email_login_code(
        self,
        email: str,
        code: str,
        max_attempts: int,
        window_seconds: int,
    ) -> UserId | None:
        """Return the user id on success, ``None`` on a wrong code.

        Raises ``TooManyOtpAttempts`` once the email is over ``max_attempts``.
        """
        ...
