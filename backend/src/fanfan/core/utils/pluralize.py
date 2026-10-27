from typing import NamedTuple


class Plurals(NamedTuple):
    one: str
    three: str
    five: str


def pluralize(value: int, strings: Plurals) -> str:
    if (value % 10 == 1) and (value % 100 != 11):
        return strings.one
    if (2 <= value % 10 <= 4) and (value % 100 < 10 or value % 100 >= 20):
        return strings.three
    return strings.five
