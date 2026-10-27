import pytest

from fanfan.core.utils.pluralize import Plurals, pluralize

pytestmark = pytest.mark.unit

_FORM = Plurals(one="one", three="three", five="five")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, "one"),
        (21, "one"),
        (101, "one"),
        (1001, "one"),
        (2, "three"),
        (3, "three"),
        (4, "three"),
        (22, "three"),
        (104, "three"),
        (5, "five"),
        (10, "five"),
        (0, "five"),
        (100, "five"),
        (11, "five"),
        (12, "five"),
        (13, "five"),
        (14, "five"),
        (111, "five"),
        (112, "five"),
    ],
)
def test_pluralize_selects_russian_form(value: int, expected: str) -> None:
    assert pluralize(value, _FORM) == expected
