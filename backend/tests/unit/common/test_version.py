from pathlib import Path

import pytest

from fanfan.common.version import read_build_id

pytestmark = pytest.mark.unit


def test_build_id_is_read_from_the_baked_file(tmp_path: Path) -> None:
    path = tmp_path / "BUILD_ID"
    path.write_text("1a2b3c4d\n", encoding="utf-8")

    assert read_build_id(path) == "1a2b3c4d"


def test_missing_file_means_no_build_id(tmp_path: Path) -> None:
    assert read_build_id(tmp_path / "BUILD_ID") is None


def test_empty_file_means_no_build_id(tmp_path: Path) -> None:
    # A local image build passes no APP_BUILD, so the Dockerfile writes an empty
    # file; it must not become a blank Sentry release.
    path = tmp_path / "BUILD_ID"
    path.write_text("", encoding="utf-8")

    assert read_build_id(path) is None
