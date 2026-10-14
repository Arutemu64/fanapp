from pathlib import Path

from fanfan.application.ports.password_blocklist import PasswordBlocklist

_PASSWORDS_FILE = Path(__file__).parent / "data" / "common_passwords.txt"


class WordListPasswordBlocklist(PasswordBlocklist):
    """Blocklist backed by a vendored list of the most common passwords.

    The list is loaded once at construction; the blocklist is stateless and safe
    to share as an application-scoped singleton. Matching is case-insensitive so
    "Password123" falls with "password123": a capital letter is the cheapest
    variation a user makes, and the list holds every entry casefolded.
    """

    def __init__(self) -> None:
        lines = _PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
        self._blocked = frozenset(line for line in lines if line)

    def is_blocked(self, password: str) -> bool:
        return password.casefold() in self._blocked
