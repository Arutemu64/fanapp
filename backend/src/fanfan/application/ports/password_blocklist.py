from typing import Protocol


class PasswordBlocklist(Protocol):
    def is_blocked(self, password: str) -> bool:
        """Return True if the password is a known commonly used or leaked value.

        Compared as a whole, not by substring: NIST SP 800-63B-4 §3.1.1 asks for
        a blocklist check on the entire chosen password only.
        """
        ...
