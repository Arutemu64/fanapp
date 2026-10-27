import re
from itertools import product
from typing import Any, cast

import pytest

from fanfan.adapters.profanity.filter import WordListProfanityFilter
from fanfan.application.services.user import (
    FEMININE_NOUNS,
    MASCULINE_NOUNS,
    RUSSIAN_ADJECTIVES,
    UserService,
)
from fanfan.core.vo.fields import USERNAME_PATTERN

pytestmark = pytest.mark.unit

MASCULINE_ADJECTIVES = tuple(masculine for masculine, _ in RUSSIAN_ADJECTIVES)
FEMININE_ADJECTIVES = tuple(feminine for _, feminine in RUSSIAN_ADJECTIVES)
WORD_LISTS = [
    MASCULINE_ADJECTIVES,
    FEMININE_ADJECTIVES,
    MASCULINE_NOUNS,
    FEMININE_NOUNS,
]
PAIRINGS = [
    (MASCULINE_ADJECTIVES, MASCULINE_NOUNS),
    (FEMININE_ADJECTIVES, FEMININE_NOUNS),
]

GENERATED_SHAPE = re.compile(r"^[А-Я][а-я]+[А-Я][а-я]+\d{2}$")


@pytest.mark.parametrize("words", WORD_LISTS)
def test_word_lists_have_no_duplicates(words: tuple[str, ...]) -> None:
    assert len(set(words)) == len(words)


@pytest.mark.parametrize("words", WORD_LISTS)
def test_words_avoid_yo(words: tuple[str, ...]) -> None:
    assert [word for word in words if "ё" in word.lower()] == []


@pytest.mark.parametrize(("adjectives", "nouns"), PAIRINGS)
def test_longest_pair_fits_the_username_rules(
    adjectives: tuple[str, ...], nouns: tuple[str, ...]
) -> None:
    longest = max(adjectives, key=len) + max(nouns, key=len) + "99"

    assert len(longest) <= 17
    assert re.fullmatch(USERNAME_PATTERN, longest)


@pytest.mark.parametrize(("adjectives", "nouns"), PAIRINGS)
def test_no_pair_trips_the_profanity_filter(
    adjectives: tuple[str, ...], nouns: tuple[str, ...]
) -> None:
    profanity_filter = WordListProfanityFilter()
    flagged = [
        adjective + noun
        for adjective, noun in product(adjectives, nouns)
        if profanity_filter.contains_profanity(adjective + noun)
    ]

    assert flagged == []


class _TakenUsernames:
    def __init__(self, taken_count: int) -> None:
        self.remaining_taken = taken_count
        self.lookups: list[str] = []

    async def get_by_username(self, username: str) -> object | None:
        self.lookups.append(username)
        if self.remaining_taken:
            self.remaining_taken -= 1
            return object()
        return None


async def test_generate_username_retries_until_a_free_name() -> None:
    gateway = _TakenUsernames(taken_count=2)
    service = UserService(cast("Any", gateway))

    username = await service.generate_username()

    assert GENERATED_SHAPE.fullmatch(username)
    assert gateway.lookups[-1] == username
    assert len(gateway.lookups) == 3


async def test_generated_adjective_agrees_with_its_noun() -> None:
    agreeing = {
        adjective + noun
        for adjectives, nouns in PAIRINGS
        for adjective, noun in product(adjectives, nouns)
    }
    service = UserService(cast("Any", _TakenUsernames(taken_count=0)))

    for _ in range(200):
        username = await service.generate_username()
        assert username[:-2] in agreeing
