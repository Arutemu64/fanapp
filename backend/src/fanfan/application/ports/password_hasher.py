from typing import Protocol


class PasswordHasher(Protocol):
    """Hashes and verifies user passwords.

    Keeps the hashing algorithm (and its tuning) an infrastructure detail:
    the application layer only depends on this port, never on a concrete
    crypto library.
    """

    def hash(self, password: str) -> str: ...

    def verify(self, password: str, hashed_password: str) -> bool: ...
