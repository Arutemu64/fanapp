from typing import Protocol


class ProfanityFilter(Protocol):
    def contains_profanity(self, text: str) -> bool:
        """Return True if the text contains profanity.

        Implementations are expected to normalize the text first (lowercase,
        fold look-alike characters, strip separators) so that obfuscated forms
        like " х.у.й" or "pizd@" are still detected.
        """
        ...
