import pytest

from fanfan.adapters.profanity.filter import WordListProfanityFilter

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def profanity_filter() -> WordListProfanityFilter:
    return WordListProfanityFilter()


@pytest.mark.parametrize(
    "value",
    [
        "хуй",
        "пиздец",  # inflected form, caught by the "пизд" root
        "ХуЙло",  # case-insensitive
        "х.у.й",  # separators stripped
        "хуууй",  # repeated letters collapsed
        "пизд@",  # leetspeak "@" -> "а"
        "xуй",  # Latin look-alike "x" folded to Cyrillic "х"
        "pizda",  # Latin transliteration from the LDNOOBW list (exact match)
        "fuck",  # English exact-match list
        "ебанько",  # inflected mat root
    ],
)
def test_detects_profanity(
    profanity_filter: WordListProfanityFilter, value: str
) -> None:
    assert profanity_filter.contains_profanity(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "tester",
        "anime_fan_2026",
        "Светлана",
        "команда",  # must not trip on the "манда" lookalike
        "требовать",  # contains "еб" but is an ordinary word
        "",
    ],
)
def test_allows_clean_text(
    profanity_filter: WordListProfanityFilter, value: str
) -> None:
    assert profanity_filter.contains_profanity(value) is False
