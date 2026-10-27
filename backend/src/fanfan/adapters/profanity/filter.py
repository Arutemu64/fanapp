import re
from pathlib import Path

from fanfan.application.ports.profanity_filter import ProfanityFilter

_DATA_DIR = Path(__file__).parent / "data"

_CONFUSABLES = {
    "a": "а",
    "b": "б",
    "c": "с",
    "e": "е",
    "h": "н",
    "k": "к",
    "m": "м",
    "o": "о",
    "p": "р",
    "t": "т",
    "x": "х",
    "y": "у",
    "0": "о",
    "1": "и",
    "3": "е",
    "@": "а",
    "$": "с",
    "ё": "е",
}

_REPEATED_LETTER = re.compile(r"(.)\1+")


def _normalize(text: str) -> str:
    folded: list[str] = []
    for char in text.casefold():
        mapped = _CONFUSABLES.get(char, char)
        if mapped.isalpha():
            folded.append(mapped)
    return _REPEATED_LETTER.sub(r"\1", "".join(folded))


def _load_normalized(filename: str) -> set[str]:
    path = _DATA_DIR / filename
    words: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        normalized = _normalize(line)
        if normalized:
            words.add(normalized)
    return words


class WordListProfanityFilter(ProfanityFilter):
    """Profanity filter backed by static word lists.

    Two matching strategies are combined:

    * Exact match against the vendored LDNOOBW lists (whole normalized token).
      Exact matching keeps false positives low even though those lists contain
      some mild words and multi-word phrases.
    * Substring match against a curated set of unambiguous mat roots, which
      catches inflected and obfuscated forms ("пиздец", "ебанько", ...).

    The lists are loaded once at construction; the filter is stateless and
    safe to share as an application-scoped singleton.
    """

    def __init__(self) -> None:
        self._exact = frozenset(
            _load_normalized("ldnoobw_ru.txt") | _load_normalized("ldnoobw_en.txt")
        )
        self._roots = frozenset(_load_normalized("roots_ru.txt"))

    def contains_profanity(self, text: str) -> bool:
        normalized = _normalize(text)
        if not normalized:
            return False
        if normalized in self._exact:
            return True
        return any(root in normalized for root in self._roots)
