import pytest

from fanfan.presentation.web.preconditions import if_none_match_hits, parse_if_match

pytestmark = pytest.mark.unit


def test_if_none_match_absent_header_never_hits() -> None:
    assert if_none_match_hits(None, '"abc"') is False


def test_if_none_match_matches_the_exact_validator() -> None:
    assert if_none_match_hits('"abc"', '"abc"') is True
    assert if_none_match_hits('"def"', '"abc"') is False


def test_if_none_match_matches_within_a_list() -> None:
    # Clients may send several cached validators, comma-separated.
    assert if_none_match_hits('"x", "abc", "y"', '"abc"') is True


def test_if_none_match_star_matches_any_version() -> None:
    assert if_none_match_hits("*", '"abc"') is True


def test_if_match_lists_every_entity_tag() -> None:
    assert parse_if_match('"x", "abc"') == frozenset({'"x"', '"abc"'})


def test_if_match_star_is_unconditional() -> None:
    assert parse_if_match("*") is None
