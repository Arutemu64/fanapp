import io
from collections.abc import Sequence

import pytest
import xlsxwriter

from fanfan.adapters.parsers.schedule import REQUIRED_COLUMNS, parse_schedule_from_excel
from fanfan.application.interactors.schedule_mgmt.import_schedule import ScheduleEntry
from fanfan.common.paths import REPO_ROOT
from fanfan.core.exceptions.schedule import (
    InvalidScheduleFile,
    InvalidScheduleFileReason,
)

pytestmark = pytest.mark.unit

TEMPLATE_PATH = REPO_ROOT / "frontend" / "static" / "schedule-template.xlsx"

VALID_ROW = {
    "number": 1,
    "title": "Открытие фестиваля",
    "duration": 15,
    "nomination_title": "Вне конкурса",
    "block_title": "Открытие",
}


def valid_row(**overrides: object) -> tuple[object, ...]:
    """A row that parses cleanly, in REQUIRED_COLUMNS order, with cells swapped."""
    cells = VALID_ROW | overrides
    return tuple(cells[column] for column in REQUIRED_COLUMNS)


def build_sheet(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> io.BytesIO:
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet()
    for column_index, header in enumerate(headers):
        worksheet.write_string(0, column_index, header)
    for row_index, row in enumerate(rows, start=1):
        for column_index, value in enumerate(row):
            worksheet.write(row_index, column_index, value)
    workbook.close()
    buffer.seek(0)
    return buffer


def test_parses_the_downloadable_template() -> None:
    """The template offered on the import screen must parse as-is.

    This is the drift guard for a committed binary: change the columns the
    parser requires without regenerating the template
    (`just backend-generate-schedule-template`) and this fails.
    """
    with TEMPLATE_PATH.open("rb") as file:
        schedule = parse_schedule_from_excel(file)

    assert schedule == [
        ScheduleEntry(
            number=1,
            title="Открытие фестиваля",
            duration=15,
            nomination_title="Вне конкурса",
            block_title="Открытие",
        ),
        ScheduleEntry(
            number=2,
            title="Дефиле «Наруто»",
            duration=5,
            nomination_title="Одиночное дефиле",
            block_title="Косплей",
        ),
        ScheduleEntry(
            number=3,
            title="Сценка «Стальной алхимик»",
            duration=8,
            nomination_title="Групповое дефиле",
            block_title="Косплей",
        ),
        ScheduleEntry(
            number=4,
            title="Вокал: «Унесённые призраками»",
            duration=6,
            nomination_title="Вокал",
            block_title="Караоке",
        ),
        ScheduleEntry(
            number=5,
            title="Награждение и закрытие",
            duration=20,
            nomination_title="Вне конкурса",
            block_title="Закрытие",
        ),
    ]


def test_column_order_does_not_matter() -> None:
    sheet = build_sheet(
        ["block_title", "duration", "number", "nomination_title", "title"],
        [("Открытие", 15, 1, "Вне конкурса", "Открытие фестиваля")],
    )

    assert parse_schedule_from_excel(sheet) == [ScheduleEntry(**VALID_ROW)]


def test_accepts_whole_numbers_stored_as_floats() -> None:
    # Excel has no integer type, so a hand-typed 1 can arrive as 1.0.
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(number=1.0, duration=15.0)])

    schedule = parse_schedule_from_excel(sheet)

    assert schedule[0].number == 1
    assert schedule[0].duration == 15


def test_rejects_a_file_that_is_not_a_spreadsheet() -> None:
    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(io.BytesIO(b"definitely not a spreadsheet"))

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.UNREADABLE_FILE


def test_reports_every_missing_column_at_once() -> None:
    sheet = build_sheet(["number", "title", "block_title"], [(1, "Открытие", "Блок")])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.MISSING_COLUMNS
    assert exc_info.value.details["columns"] == ["duration", "nomination_title"]


def test_rejects_an_empty_sheet() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.EMPTY_FILE


@pytest.mark.parametrize("column", ["title", "nomination_title", "block_title"])
def test_rejects_a_blank_text_cell(column: str) -> None:
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [valid_row(), valid_row(number=2, **{column: "   "})],
    )

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.EMPTY_CELL
    assert exc_info.value.details["column"] == column
    # Row 1 is the header and row 2 is the valid entry, so the bad one is row 3.
    assert exc_info.value.details["row"] == 3


@pytest.mark.parametrize("column", ["number", "duration"])
def test_rejects_a_non_integer_number(column: str) -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(**{column: "пять"})])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.INVALID_NUMBER
    assert exc_info.value.details["column"] == column
    assert exc_info.value.details["row"] == 2


def test_rejects_a_fractional_duration() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(duration=7.5)])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.INVALID_NUMBER
    assert exc_info.value.details["column"] == "duration"


def test_rejects_a_repeated_number() -> None:
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(), valid_row(title="Другое")])

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert (
        exc_info.value.details["reason"] == InvalidScheduleFileReason.DUPLICATE_NUMBER
    )
    assert exc_info.value.details["number"] == 1
    assert exc_info.value.details["row"] == 3
