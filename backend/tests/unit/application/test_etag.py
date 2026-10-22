import pytest

from fanfan.application.services.etag import compute_strong_etag

pytestmark = pytest.mark.unit


def test_compute_strong_etag_is_a_quoted_strong_validator() -> None:
    etag = compute_strong_etag('{"schedule":[]}')
    # Strong validator: quoted, no weak W/ prefix.
    assert etag.startswith('"')
    assert etag.endswith('"')
    assert not etag.startswith("W/")


def test_compute_strong_etag_changes_with_payload() -> None:
    assert compute_strong_etag('{"a":1}') != compute_strong_etag('{"a":2}')
    # Same bytes in, same ETag out — the read must be reproducible.
    assert compute_strong_etag('{"a":1}') == compute_strong_etag('{"a":1}')
