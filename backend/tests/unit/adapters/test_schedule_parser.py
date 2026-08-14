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
    "duration": 900,
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
            number=None,
            title="Открытие фестиваля",
            duration=900,
            nomination_title=None,
            block_title=None,
        ),
        ScheduleEntry(
            number=1,
            title="Дефиле «Наруто»",
            duration=45,
            nomination_title="Одиночное дефиле",
            block_title="Косплей",
        ),
        ScheduleEntry(
            number=2,
            title="Сценка «Стальной алхимик»",
            duration=480,
            nomination_title="Групповое дефиле",
            block_title="Косплей",
        ),
        ScheduleEntry(
            number=None,
            title="Перерыв",
            duration=600,
            nomination_title=None,
            block_title=None,
        ),
        ScheduleEntry(
            number=3,
            title="Вокал: «Унесённые призраками»",
            duration=210,
            nomination_title="Вокал",
            block_title="Караоке",
        ),
        ScheduleEntry(
            number=None,
            title="Награждение и закрытие",
            duration=1200,
            nomination_title=None,
            block_title=None,
        ),
    ]


def test_column_order_does_not_matter() -> None:
    sheet = build_sheet(
        ["block_title", "duration", "number", "nomination_title", "title"],
        [("Открытие", 900, 1, "Вне конкурса", "Открытие фестиваля")],
    )

    assert parse_schedule_from_excel(sheet) == [ScheduleEntry(**VALID_ROW)]


def test_accepts_whole_numbers_stored_as_floats() -> None:
    # Excel has no integer type, so a hand-typed 1 can arrive as 1.0.
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(number=1.0, duration=900.0)])

    schedule = parse_schedule_from_excel(sheet)

    assert schedule[0].number == 1
    assert schedule[0].duration == 900


def test_accepts_a_sub_minute_duration() -> None:
    # `duration` is seconds, so an act shorter than a minute is an ordinary
    # value rather than something to round up — a single defile really does run
    # under a minute.
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(duration=45)])

    assert parse_schedule_from_excel(sheet)[0].duration == 45


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


def test_rejects_a_blank_title() -> None:
    # `title` is a row's only human identity, so it stays required even though
    # nomination and block no longer are.
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [valid_row(), valid_row(number=2, title="   ")],
    )

    with pytest.raises(InvalidScheduleFile) as exc_info:
        parse_schedule_from_excel(sheet)

    assert exc_info.value.details["reason"] == InvalidScheduleFileReason.EMPTY_CELL
    assert exc_info.value.details["column"] == "title"
    # Row 1 is the header and row 2 is the valid entry, so the bad one is row 3.
    assert exc_info.value.details["row"] == 3


@pytest.mark.parametrize("column", ["nomination_title", "block_title"])
@pytest.mark.parametrize("blank", [None, "", "   "])
def test_accepts_a_blank_nomination_or_block(column: str, blank: object) -> None:
    # Breaks, the opening and the closing carry no nomination or block, so those
    # cells may be blank — an empty cell, an empty string or whitespace all read
    # back as None rather than forcing an invented placeholder.
    sheet = build_sheet(REQUIRED_COLUMNS, [valid_row(**{column: blank})])

    schedule = parse_schedule_from_excel(sheet)

    assert getattr(schedule[0], column) is None


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


def test_accepts_an_empty_number() -> None:
    # Breaks carry no public number, so `number` is the one column that may be
    # left blank.
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [valid_row(), valid_row(number=None, title="Перерыв")],
    )

    schedule = parse_schedule_from_excel(sheet)

    assert [entry.number for entry in schedule] == [1, None]


def test_accepts_several_numberless_rows() -> None:
    # Numberless rows match no existing event, so they never collide the way two
    # rows sharing a number would.
    sheet = build_sheet(
        REQUIRED_COLUMNS,
        [
            valid_row(number=None, title="Перерыв"),
            valid_row(number=None, title="Технический перерыв"),
        ],
    )

    schedule = parse_schedule_from_excel(sheet)

    assert [entry.number for entry in schedule] == [None, None]
