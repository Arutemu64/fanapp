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
        "пиздец",
        "ХуЙло",
        "х.у.й",
        "хуууй",
        "пизд@",
        "xуй",
        "pizda",
        "fuck",
        "ебанько",
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
        "команда",
        "требовать",
        "",
    ],
)
def test_allows_clean_text(
    profanity_filter: WordListProfanityFilter, value: str
) -> None:
    assert profanity_filter.contains_profanity(value) is False
