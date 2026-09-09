import pytest

from fanfan.core.utils.pluralize import (
    NOTIFICATIONS_PLURALS,
    POINTS_PLURALS,
    SECONDS_PLURALS,
    Plurals,
    pluralize,
)

pytestmark = pytest.mark.unit

_FORM = Plurals(one="one", three="three", five="five")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # ...1 but not ...11 -> "one" form
        (1, "one"),
        (21, "one"),
        (101, "one"),
        (1001, "one"),
        # ...2-4 but not ...12-14 -> "three" form
        (2, "three"),
        (3, "three"),
        (4, "three"),
        (22, "three"),
        (104, "three"),
        # everything else -> "five" form
        (5, "five"),
        (10, "five"),
        (0, "five"),
        (100, "five"),
        # The teens (11-14) are the exception the "one"/"three" rules exclude.
        (11, "five"),
        (12, "five"),
        (13, "five"),
        (14, "five"),
        (111, "five"),
        (112, "five"),
    ],
)
def test_pluralize_selects_russian_form(value: int, expected: str):
    assert pluralize(value, _FORM) == expected


def test_pluralize_uses_the_given_strings():
    assert pluralize(1, SECONDS_PLURALS) == "секунду"
    assert pluralize(3, POINTS_PLURALS) == "очка"
    assert pluralize(5, NOTIFICATIONS_PLURALS) == "уведомлений"
