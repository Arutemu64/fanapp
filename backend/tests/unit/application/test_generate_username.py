import re
from itertools import product
from typing import Any, cast

import pytest

from fanfan.adapters.profanity.filter import WordListProfanityFilter
from fanfan.application.services.user import (
    RUSSIAN_ADJECTIVES,
    RUSSIAN_NOUNS,
    UserService,
)
from fanfan.core.vo.fields import USERNAME_PATTERN

pytestmark = pytest.mark.unit

GENERATED_SHAPE = re.compile(r"^[А-Я][а-я]+[А-Я][а-я]+\d{2}$")


@pytest.mark.parametrize("words", [RUSSIAN_ADJECTIVES, RUSSIAN_NOUNS])
def test_word_lists_have_no_duplicates(words: tuple[str, ...]) -> None:
    assert len(set(words)) == len(words)


@pytest.mark.parametrize("words", [RUSSIAN_ADJECTIVES, RUSSIAN_NOUNS])
def test_words_avoid_yo(words: tuple[str, ...]) -> None:
    assert [word for word in words if "ё" in word.lower()] == []


def test_longest_pair_fits_the_username_rules() -> None:
    longest = max(RUSSIAN_ADJECTIVES, key=len) + max(RUSSIAN_NOUNS, key=len) + "99"

    # Well under the 25-character limit on purpose: the quest leaderboard gives
    # a name about 130px on a 360px phone, where each word of a 17-character
    # name still fits its own line; longer words start breaking mid-word.
    assert len(longest) <= 17
    assert re.fullmatch(USERNAME_PATTERN, longest)


def test_no_pair_trips_the_profanity_filter() -> None:
    # A user who keeps the generated name and edits nothing else must not be
    # told their own name is profane, and the filter matches roots across the
    # adjective/noun seam.
    profanity_filter = WordListProfanityFilter()
    flagged = [
        adjective + noun
        for adjective, noun in product(RUSSIAN_ADJECTIVES, RUSSIAN_NOUNS)
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
