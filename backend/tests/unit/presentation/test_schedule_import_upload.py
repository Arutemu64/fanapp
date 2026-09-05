import io

import pytest
from starlette.datastructures import Headers, UploadFile

from fanfan.core.exceptions.schedule import (
    InvalidScheduleFile,
    InvalidScheduleFileReason,
)
from fanfan.presentation.web.routes.schedule.importing import (
    _MAX_IMPORT_BYTES,
    _ensure_valid_upload,
)

pytestmark = pytest.mark.unit


def _upload(
    *,
    size: int = 1024,
    filename: str = "schedule.xlsx",
    content_type: str | None = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ),
) -> UploadFile:
    headers = Headers({"content-type": content_type}) if content_type else Headers()
    return UploadFile(
        io.BytesIO(b"\x00" * size), size=size, filename=filename, headers=headers
    )


def test_accepts_a_small_xlsx_upload() -> None:
    _ensure_valid_upload(_upload())


def test_accepts_the_octet_stream_content_type_browsers_send_for_xlsx() -> None:
    _ensure_valid_upload(_upload(content_type="application/octet-stream"))


def test_rejects_an_oversized_upload() -> None:
    with pytest.raises(InvalidScheduleFile) as exc_info:
        _ensure_valid_upload(_upload(size=_MAX_IMPORT_BYTES + 1))

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.FILE_TOO_LARGE


def test_rejects_a_non_xlsx_filename() -> None:
    with pytest.raises(InvalidScheduleFile) as exc_info:
        _ensure_valid_upload(_upload(filename="schedule.csv"))

    assert (
        exc_info.value.details["reason"]
        == InvalidScheduleFileReason.UNSUPPORTED_FILE_TYPE
    )


def test_rejects_an_unexpected_content_type() -> None:
    with pytest.raises(InvalidScheduleFile) as exc_info:
        _ensure_valid_upload(_upload(content_type="text/csv"))

    assert (
        exc_info.value.details["reason"]
        == InvalidScheduleFileReason.UNSUPPORTED_FILE_TYPE
    )
