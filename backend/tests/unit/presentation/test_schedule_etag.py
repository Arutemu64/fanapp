import pytest

from fanfan.application.interactors.schedule.get_schedule import _compute_etag
from fanfan.presentation.web.routes.schedule.public import _if_none_match_hits

pytestmark = pytest.mark.unit


def test_compute_etag_is_a_quoted_strong_validator():
    etag = _compute_etag('{"schedule":[]}')
    # Strong validator: quoted, no weak W/ prefix.
    assert etag.startswith('"')
    assert etag.endswith('"')
    assert not etag.startswith("W/")


def test_compute_etag_changes_with_payload():
    assert _compute_etag('{"a":1}') != _compute_etag('{"a":2}')
    # Same bytes in, same ETag out — the read must be reproducible.
    assert _compute_etag('{"a":1}') == _compute_etag('{"a":1}')


def test_if_none_match_absent_header_never_hits():
    assert _if_none_match_hits(None, '"abc"') is False


def test_if_none_match_matches_the_exact_validator():
    assert _if_none_match_hits('"abc"', '"abc"') is True
    assert _if_none_match_hits('"def"', '"abc"') is False


def test_if_none_match_matches_within_a_list():
    # Clients may send several cached validators, comma-separated.
    assert _if_none_match_hits('"x", "abc", "y"', '"abc"') is True


def test_if_none_match_star_matches_any_version():
    assert _if_none_match_hits("*", '"abc"') is True
