from typing import NamedTuple


class Plurals(NamedTuple):
    one: str
    three: str
    five: str


def pluralize(value: int, strings: Plurals) -> str:
    if (value % 10 == 1) and (value % 100 != 11):
        # e.g. "1 секунду"
        return strings.one
    if (2 <= value % 10 <= 4) and (value % 100 < 10 or value % 100 >= 20):
        # e.g. "3 секунды"
        return strings.three
    # e.g. "5 секунд"
    return strings.five
